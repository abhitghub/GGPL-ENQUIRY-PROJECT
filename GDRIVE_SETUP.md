# Save quotations to Google Drive (Excel, named by customer + date)

The portal writes each enquiry/quotation to Google Drive as an **Excel file**
named **`<customer> - <YYYY-MM-DD>.xlsx`** (the portal's Excel format):
- **on quotation generation**, and
- **nightly** — a full export of every enquiry/quotation (the `exporter` service).

Your Google organization **blocks service-account keys**, so we use the simplest
method that avoids Google Cloud entirely: **Google Drive for Desktop**. The app
writes the Excel files into a normal folder on this PC, and Drive for Desktop
syncs that folder to your Google Drive.

## 1. Install Google Drive for Desktop (on this server PC)
1. Download & install from https://www.google.com/drive/download/ .
2. Sign in with the Google account that owns your target Drive folder.
3. Open Drive for Desktop → Settings (gear) → **Google Drive** → choose
   **“Mirror files”** (this keeps real files on disk, which the app can write to).
   Note the local location it uses for **“My Drive”**, e.g.
   `G:\My Drive` or `C:\Users\<you>\My Drive`.

## 2. Pick the folder the files should land in
Use the Drive folder you shared earlier
(`https://drive.google.com/drive/folders/1zo_0EMTFkbHemTxq-R1eaYaADuDjFfCM`).
Find its **local mirrored path**, e.g.
`G:\My Drive\GGPL Enquiries` (whatever you named that folder).

## 3. Point the app at that folder — set it in `.env`
```
GDRIVE_EXPORT_ENABLED=true
GDRIVE_HOST_DIR=G:\My Drive\GGPL Enquiries
```
(Use *your* actual mirrored path from step 2. If the path has spaces, keep it
unquoted in `.env` — Docker handles it.)

Then apply:
```
docker compose -f docker-compose.prod.yml up -d
```

## 4. Test it now
```
docker compose -f docker-compose.prod.yml exec -e GDRIVE_EXPORT_ENABLED=true exporter python -m app.scripts.export_all_to_drive
```
You should see `Exported N/N records`, `.xlsx` files appear in the folder, and
Drive for Desktop syncs them to Drive within seconds. Generating a quotation in
the app also drops its file there automatically.

## If you don't set GDRIVE_HOST_DIR
The files are written to `./gdrive-out` inside the project folder (default). You
can then add that folder to Drive for Desktop (**Settings → My Computer → Add
folder**) — the files appear in Drive under **Computers**, not your My Drive
folder. Setting `GDRIVE_HOST_DIR` to the mirrored My Drive path (step 3) is the
way to land them in your exact folder.

## Notes
- Until `GDRIVE_EXPORT_ENABLED=true`, this is a safe no-op — the app runs normally.
- Files overwrite per customer per day (no duplicates).
- No Google Cloud / API keys needed with this method.

---

### Alternative (only if your org later allows service-account keys)
Set instead in `.env`: `GDRIVE_EXPORT_ENABLED=true`,
`GDRIVE_FOLDER_ID=<folder id>`, place the key at `secrets/gdrive-sa.json`, and
leave `GDRIVE_LOCAL_DIR` empty (folder mode takes precedence when set). The app
then uploads via the Drive API.
