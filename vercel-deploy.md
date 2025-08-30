# Deploying to Vercel

## Prerequisites
1. Install Vercel CLI: `npm i -g vercel`
2. Login: `vercel login`

## Deployment Steps

1. **Set Environment Variables in Vercel Dashboard:**
   ```bash
   # Copy your current .env values to Vercel project settings
   # Or set them via CLI:
   vercel env add GOOGLE_KEY
   vercel env add GOOGLE_CX
   vercel env add BGG_USERNAME
   vercel env add BGG_PASS
   vercel env add TELEGRAM_TOKEN
   vercel env add TELEGRAM_CHAT_ID
   vercel env add FIRESTORE_KEY
   ```

2. **Deploy:**
   ```bash
   vercel --prod
   ```

## Testing the Deployment

Test these endpoints after deployment:

1. **Manual mapping form:**
   ```
   GET https://your-app.vercel.app/
   ```

2. **Barcode lookup:**
   ```
   GET https://your-app.vercel.app/?query=634482735077
   ```

3. **Barcode lookup with redirect:**
   ```
   GET https://your-app.vercel.app/?query=634482735077&redirect=1
   ```

4. **Play registration:**
   ```
   GET https://your-app.vercel.app/?query=634482735077&play=1
   ```

## Key Changes Made for Vercel

1. **File Structure:**
   - Moved main function to `api/main.py` (Vercel serverless function)
   - Added path manipulation to import `game_scanner` modules
   - Changed from GCF Request object to Flask request object

2. **Configuration:**
   - `vercel.json` routes all traffic to the API function
   - `.vercelignore` excludes unnecessary files
   - Template folder path adjusted for Vercel structure

3. **Dependencies:**
   - Same `requirements.txt` works for both GCF and Vercel
   - Flask app structure compatible with Vercel's Python runtime

## Differences from Google Cloud Functions

- **URL Structure:** `your-app.vercel.app/` instead of `cloud-function-url`
- **Deployment:** `vercel --prod` instead of `make deploy`
- **Environment:** Vercel dashboard instead of GCF console
- **Logs:** `vercel logs` instead of GCP logging console