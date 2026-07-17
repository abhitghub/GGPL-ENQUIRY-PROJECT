# Save quotations to Google Drive (Excel, named by customer + date)

The portal can automatically write each enquiry/quotation to your Google Drive
folder as an **Excel file** named **`<customer> - <YYYY-MM-DD>.xlsx`** (the same
Excel the portal generates). It writes:
- **on quotation generation** (each generated quotation), and
- **nightly** — a full export of every enquiry/quotation (a background `exporter`
  service).

Target folder (yours):
`https://drive.google.com/drive/folders/1zo_0EMTFkbHemTxq-R1eaYaADuDjFfCM`
(folder id `1zo_0EMTFkbHemTxq-R1eaYaADuDjFfCM`)

Because the server is headless (Docker), it authenticates with a **Google service
account**. One-time setup (~5–10 min):

## 1. Create a service account + key
1. Go to https://console.cloud.google.com/ → create/select a project.
2. **APIs & Services → Library** → search **Google Drive API** → **Enable**.
3. **APIs & Services → Credentials → Create credentials → Service account**.
   Give it a name (e.g. `ggpl-quote-export`), Create → Done.
4. Open that service account → **Keys → Add key → Create new key → JSON** →
   download the file. Note the service account **email**
   (looks like `ggpl-quote-export@<project>.iam.gserviceaccount.com`).

## 2. Share the Drive folder with the service account
1. Open the Drive folder (link above).
2. **Share** → paste the service account **email** → give it **Editor** → Send.
   (This is what lets the server write files into *your* folder.)

## 3. Put the key on the server
1. Copy the downloaded JSON to this project's `secrets` folder as:
   `secrets/gdrive-sa.json`
   (full path: `...\goodrich\secrets\gdrive-sa.json`). This folder is gitignored.

## 4. Turn it on
In your `.env` add:
```
GDRIVE_EXPORT_ENABLED=true
GDRIVE_FOLDER_ID=1zo_0EMTFkbHemTxq-R1eaYaADuDjFfCM
```
Then apply:
```
docker compose -f docker-compose.prod.yml up -d
```

## 5. Test it now (optional)
Run the full export immediately instead of waiting for the nightly job:
```
docker compose -f docker-compose.prod.yml exec exporter python -m app.scripts.export_all_to_drive
```
You should see `Exported N/N records to Drive`, and the `.xlsx` files appear in
the Drive folder within seconds. Generating a quotation in the app also drops its
file there automatically.

## Notes
- Files are **upserted by name** — re-exporting the same customer on the same day
  overwrites that file (no duplicates per day).
- Until the key is present and `GDRIVE_EXPORT_ENABLED=true`, the feature is a safe
  no-op — the app runs normally and nothing is written.
- The service account only gets access to **this one shared folder**, nothing else
  in your Drive.
- Keep `secrets/gdrive-sa.json` private — it's a credential (already gitignored).
