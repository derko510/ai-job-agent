# Dashboard refresh (every 30 min)

Keep this run as short as possible. It is bookkeeping, not research. Stay on Haiku.

1. In this job-hunt folder run with Bash: `python3 -I publish_dashboard.py`
   This is a plain Python script with no AI. It merges new application results and rebuilds the data files.
2. Read its LAST line of output:
   - If it is `NOCHANGE`, reply "no change" and STOP. Do nothing else.
   - If it starts with `PUBLISH `, the rest of the line is a JSON list of {file, dataset, name}. Continue to step 3.
3. For each entry, call the Artifact tool once with:
   - action "publish"
   - url = dashboard_url from profile.json
   - asset true
   - file_path = file
   Note each returned /_blob/<id> url. Do not open or read the files.
4. Call ArtifactData (load it with ToolSearch if deferred) with action "list", the dashboard url, and collection "datasets" to get each
   dataset's version.
5. Call ArtifactData ONCE with action "batch". For each entry, add an "update" write with:
   - collection "datasets"
   - doc_id = dataset
   - if_version = the version you read
   - data = {"source": {"kind": "file", "format": "json", "name": <name>, "url": <new blob url>}, "updated": {"at": <now, UTC ISO>, "by": "Claude"}}
   Never touch the files/ collection.
6. Free storage (the artifact has a 1 GB file limit, and old copies pile up until it is full):
   only if the batch succeeded, for each entry take the dataset's OLD source.url from the step 4 list. If it is a
   /_blob/<id> url and differs from the new one, call Artifact with action "delete", url = dashboard_url from profile.json
   and path = <id>. Never delete anything else. A failed delete is fine.
7. If the batch succeeded, run `python3 -I publish_dashboard.py --done`, then
   `python3 -I activity_log.py publish "dashboard refreshed (N files)"`.
8. Reply with one line: "published N files" or "failed: <reason>". On failure log it with `activity_log.py error`.
