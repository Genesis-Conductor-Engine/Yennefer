import os
import stripe
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# CONFIGURATION
# Ensure you export this env var: export STRIPE_SECRET_KEY="sk_test_..."
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
DOMAIN = os.getenv("DOMAIN", "https://yennefer.genesisconductor.io")
ARTIFACT_PATH = "/opt/genesis-q-mem/install_qmem_stack.sh" # The Product

app = FastAPI()

# 1. MOUNT THE REACT UI (The Face)
# This serves your built React app at the root URL
# Note: We mount the assets folder specifically
app.mount("/assets", StaticFiles(directory="commerce-ui/dist/assets"), name="assets")

@app.get("/")
async def read_root():
    # Serve the main index.html entry point
    return FileResponse("commerce-ui/dist/index.html")

# 2. THE COMMERCE ENDPOINTS (The Logic)

@app.post("/api/create-checkout-session")
async def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Instinct Protocol Node (v1)',
                        'description': '20B BOSS Container + Net-Metering Daemon',
                    },
                    'unit_amount': 4900,
                },
                'quantity': 1,
            }],
            mode='payment',
            # React handles the verify/success state, so we just return to the UI
            success_url=f"{DOMAIN}/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{DOMAIN}/",
        )
        return {"url": session.url}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

@app.get("/api/verify-session")
async def verify_session(session_id: str):
    """The Airlock Verification"""
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            return {
                "status": "verified",
                "customer_email": session.customer_details.email,
                "manifest": ["BOSS Container", "Dual-Lateral Bridge", "Net-Metering Daemon"]
            }
        else:
            return {"status": "pending"}
    except:
        return {"status": "invalid"}

@app.get("/api/download")
async def download_artifact(session_id: str):
    """Serve the Payload"""
    # Double-check payment before serving bytes
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            # In a real scenario, ensure ARTIFACT_PATH exists
            if os.path.exists(ARTIFACT_PATH):
                return FileResponse(
                    ARTIFACT_PATH,
                    media_type='application/x-sh',
                    filename="instinct_installer.sh"
                )
            return {"error": "Artifact generation pending. Contact Administrator."}
    except:
        pass
    raise HTTPException(status_code=403, detail="Entropy Acquisition Required")
