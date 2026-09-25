"""Real MCP check: official stdio client -> this Tool's MCP server -> real jobs (including a real model search).

    runtime/python/Scripts/python.exe app/scripts/validate_mcp.py [--library "Real validation"] [--query "water flowing in a stream"]
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from config import DATA, REPORTS


async def main(arguments):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    server = StdioServerParameters(command=sys.executable, args=[str(APP/'tool.py'), '--data-dir', str(DATA/'jobs-mcp'), 'mcp'],
                                   env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    async with stdio_client(server) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            expected = {'op_check_library', 'op_suggest_names', 'op_rename_files', 'op_write_metadata', 'op_search_sounds', 'op_scan_library', 'op_analyze_library', 'op_list_models', 'op_install_model', 'cy_get_job', 'cy_cancel_job', 'cy_describe_operation'}
            assert expected <= names, sorted(expected-names)
            async def call(tool, payload, timeout=600):
                response = await session.call_tool(tool, payload)
                assert not response.isError, response
                job = json.loads(response.content[0].text)
                deadline = time.monotonic()+timeout
                while job.get('state') not in ('Completed', 'Failed', 'Cancelled'):
                    assert time.monotonic() < deadline, 'MCP job timeout'
                    await asyncio.sleep(0.2)
                    job = json.loads((await session.call_tool('cy_get_job', {'jobId': job['jobId']})).content[0].text)
                return job
            described = json.loads((await session.call_tool('cy_describe_operation', {'operationId': 'search_sounds'})).content[0].text)
            libraries = (await call('op_list_libraries', {'parameters': {}}))['outputs']['libraries']
            library = next((l for l in libraries if l['name'] == arguments.library), None)
            assert library, 'Library not found: '+arguments.library
            status = (await call('op_library_status', {'parameters': {'libraryId': library['libraryId']}}))['outputs']
            began = time.monotonic()
            search = await call('op_search_sounds', {'parameters': {'libraryId': library['libraryId'], 'text': arguments.query, 'llmAssist': 'off', 'topK': 5}})
            assert search['state'] == 'Completed', search.get('error')
            # what an assistant does when the user says "find me a sound of ...": no Library id, every Library is searched
            anywhere = await call('op_search_sounds', {'parameters': {'text': arguments.query, 'llmAssist': 'off', 'topK': 3}})
            assert anywhere['state'] == 'Completed' and anywhere['outputs']['results'][0]['libraryName'], anywhere.get('error')
            checked = (await call('op_check_library', {'parameters': {'libraryId': library['libraryId']}}))['outputs']
            suggested = (await call('op_suggest_names', {'parameters': {'libraryId': library['libraryId'], 'limit': 8}}))['outputs']       # read-only
            unconfirmed = await session.call_tool('op_rename_files', {'parameters': {'libraryId': library['libraryId'], 'renames': [{'audioId': '0'*32, 'newName': 'x.wav'}]}})
            assert unconfirmed.isError or 'InvalidParameters' in unconfirmed.content[0].text, 'rename_files accepted a call without confirm'
            invalid = await call('op_search_sounds', {'parameters': {'libraryId': library['libraryId']}})
            assert invalid['state'] == 'Failed' and invalid['error']['code'] == 'InvalidParameters', invalid
            refused = await call('op_install_model', {'parameters': {'modelKey': 'm2d-clap@2024'}})      # no acceptLicense: must be refused
            assert refused['state'] == 'Failed' and refused['error']['code'] == 'LicenseAcceptanceRequired', refused
            # working folder by folder, read-only: the tree, then the files of its largest folder through the same filter
            tree = (await call('op_list_folders', {'parameters': {'libraryId': library['libraryId'], 'maxDepth': 1}}))['outputs']
            root, folder = max(((r, f) for r in tree['roots'] for f in r['folders']), key=lambda pair: pair[1]['files'])
            page = (await call('op_browse_assets', {'parameters': {'libraryId': library['libraryId'], 'limit': 3,
                                                                   'filters': {'rootIds': [root['rootId']], 'folderPrefix': folder['path']}}}))['outputs']
            assert page['total'] == folder['files'], (page['total'], folder)
            unscoped = await call('op_update_assets', {'parameters': {'libraryId': library['libraryId'], 'filters': {}, 'addTags': ['x']}})
            assert unscoped['state'] == 'Failed' and unscoped['error']['code'] == 'InvalidParameters', 'an empty filter was accepted'
            evidence = {'transport': 'MCP stdio (official mcp client)', 'date': time.strftime('%Y-%m-%d %H:%M:%S'), 'toolCount': len(names),
                        'searchInputProperties': sorted(described['inputSchema']['properties']), 'library': {'files': status['files'], 'models': status['models']},
                        'search': {'query': arguments.query, 'seconds': round(time.monotonic()-began, 2), 'models': [m['modelKey'] for m in search['outputs']['models']],
                                   'results': [{'file': r['filename'], 'final': r['finalScore']} for r in search['outputs']['results']]},
                        'searchWithoutLibraryId': [{'file': r['filename'], 'library': r['libraryName'], 'path': r['path'], 'final': r['finalScore']} for r in anywhere['outputs']['results']],
                        'checkLibrary': {k: checked[k] for k in ('changed', 'new', 'modified', 'missing', 'unchanged')},
                        'nameSuggestions': [{'current': p['currentName'], 'proposed': p['proposedName'], 'why': p['reason']} for p in suggested['plan']],
                        'renameWithoutConfirmRefused': True,
                        'folders': {'roots': len(tree['roots']), 'topLevelFolders': sum(len(r['folders']) for r in tree['roots']),
                                    'largestFolderFiles': folder['files'], 'browseTotalWithSameFilter': page['total'],
                                    'emptyFilterEditRefused': unscoped['error']['code']},
                        'invalidParametersCode': invalid['error']['code'], 'licenceNotAcceptedCode': refused['error']['code']}
            REPORTS.mkdir(parents=True, exist_ok=True)
            (REPORTS/'mcp-validation.json').write_text(json.dumps(evidence, indent=1, ensure_ascii=False), 'utf-8')
            print(json.dumps(evidence, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--library', default='Real validation'); parser.add_argument('--query', default='water flowing in a stream')
    asyncio.run(main(parser.parse_args()))
