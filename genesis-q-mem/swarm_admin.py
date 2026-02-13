"""
Yennefer Swarm Admin Panel
FastAPI admin interface with authentication
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
import secrets
import sqlite3
from datetime import datetime
from swarm_config import SWARM_CONFIG

app = FastAPI(title="Yennefer Swarm Admin")
security = HTTPBasic()

# Admin credentials (change these!)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "yennefer2026"  # TODO: Change this!


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials"""
    is_correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    is_correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/", response_class=HTMLResponse)
async def admin_dashboard(username: str = Depends(verify_admin)):
    """Admin dashboard home"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Yennefer Swarm Admin</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-white">
        <div class="container mx-auto px-4 py-8">
            <header class="mb-8">
                <h1 class="text-4xl font-bold text-purple-400">Yennefer Swarm Admin</h1>
                <p class="text-gray-400">Logged in as: {username}</p>
            </header>

            <div class="grid md:grid-cols-3 gap-6 mb-8">
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h3 class="text-xl font-bold mb-2">System Status</h3>
                    <div id="system-status">Loading...</div>
                </div>

                <div class="bg-gray-800 p-6 rounded-lg">
                    <h3 class="text-xl font-bold mb-2">Active Users</h3>
                    <div id="user-count">Loading...</div>
                </div>

                <div class="bg-gray-800 p-6 rounded-lg">
                    <h3 class="text-xl font-bold mb-2">Total Delegations</h3>
                    <div id="delegation-count">Loading...</div>
                </div>
            </div>

            <div class="grid md:grid-cols-2 gap-6">
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h3 class="text-xl font-bold mb-4">Quick Actions</h3>
                    <div class="space-y-2">
                        <a href="/admin/users" class="block bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded text-center">Manage Users</a>
                        <a href="/admin/subscriptions" class="block bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-center">Subscriptions</a>
                        <a href="/admin/usage" class="block bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-center">Usage Stats</a>
                        <a href="/admin/config" class="block bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded text-center">Configuration</a>
                    </div>
                </div>

                <div class="bg-gray-800 p-6 rounded-lg">
                    <h3 class="text-xl font-bold mb-4">Recent Activity</h3>
                    <div id="recent-activity">Loading...</div>
                </div>
            </div>
        </div>

        <script>
            // Load system status
            fetch('/admin/api/status')
                .then(r => r.json())
                .then(data => {{
                    document.getElementById('system-status').innerHTML =
                        '<span class="text-green-400 text-2xl">● Online</span>';
                }});

            // Load user count
            fetch('/admin/api/users/count')
                .then(r => r.json())
                .then(data => {{
                    document.getElementById('user-count').innerHTML =
                        '<span class="text-3xl font-bold">' + (data.count || 0) + '</span>';
                }});

            // Load delegation count
            fetch('/admin/api/delegations/count')
                .then(r => r.json())
                .then(data => {{
                    document.getElementById('delegation-count').innerHTML =
                        '<span class="text-3xl font-bold">' + (data.count || 0) + '</span>';
                }});
        </script>
    </body>
    </html>
    """


@app.get("/admin/api/status")
async def api_status(username: str = Depends(verify_admin)):
    """Get system status"""
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {"swarm_api": "running", "mcp_server": "running", "landing_page": "running"},
    }


@app.get("/admin/api/users/count")
async def user_count(username: str = Depends(verify_admin)):
    """Get total user count"""
    try:
        conn = sqlite3.connect(str(SWARM_CONFIG["database_path"]))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return {"count": count}
    except Exception:
        return {"count": 0}


@app.get("/admin/api/delegations/count")
async def delegation_count(username: str = Depends(verify_admin)):
    """Get total delegation count"""
    try:
        conn = sqlite3.connect(str(SWARM_CONFIG["database_path"]))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM delegations")
        count = cursor.fetchone()[0]
        conn.close()
        return {"count": count}
    except Exception:
        return {"count": 0}


@app.get("/admin/users")
async def list_users(username: str = Depends(verify_admin)):
    """List all users"""
    try:
        conn = sqlite3.connect(str(SWARM_CONFIG["database_path"]))
        cursor = conn.cursor()
        cursor.execute("SELECT email, tier, created_at FROM users ORDER BY created_at DESC LIMIT 100")
        users = cursor.fetchall()
        conn.close()

        user_html = "<br>".join([f"{email} - {tier} (joined {created})" for email, tier, created in users])

        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Users - Yennefer Swarm Admin</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-900 text-white p-8">
            <h1 class="text-3xl font-bold mb-4">Users</h1>
            <a href="/" class="text-purple-400 hover:underline mb-4 block">← Back to Dashboard</a>
            <div class="bg-gray-800 p-6 rounded-lg">
                {user_html if user_html else "No users yet"}
            </div>
        </body>
        </html>
        """)
    except Exception as e:
        return HTMLResponse(f"<p>Error loading users: {str(e)}</p>")


@app.get("/admin/subscriptions")
async def list_subscriptions(username: str = Depends(verify_admin)):
    """List all active subscriptions"""
    try:
        conn = sqlite3.connect(str(SWARM_CONFIG["database_path"]))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.email, s.tier, s.status, s.current_period_end
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.status = 'active'
            ORDER BY s.current_period_end DESC
        """)
        subs = cursor.fetchall()
        conn.close()

        sub_html = "<br>".join([f"{email} - {tier} ({status}) - expires {end}" for email, tier, status, end in subs])

        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Subscriptions - Yennefer Swarm Admin</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-900 text-white p-8">
            <h1 class="text-3xl font-bold mb-4">Active Subscriptions</h1>
            <a href="/" class="text-purple-400 hover:underline mb-4 block">← Back to Dashboard</a>
            <div class="bg-gray-800 p-6 rounded-lg">
                {sub_html if sub_html else "No active subscriptions"}
            </div>
        </body>
        </html>
        """)
    except Exception as e:
        return HTMLResponse(f"<p>Error loading subscriptions: {str(e)}</p>")


@app.get("/admin/config")
async def config_panel(username: str = Depends(verify_admin)):
    """Configuration panel"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Configuration - Yennefer Swarm Admin</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-white p-8">
        <h1 class="text-3xl font-bold mb-4">System Configuration</h1>
        <a href="/" class="text-purple-400 hover:underline mb-4 block">← Back to Dashboard</a>

        <div class="bg-gray-800 p-6 rounded-lg space-y-4">
            <div>
                <h3 class="text-xl font-bold">Swarm Settings</h3>
                <p class="text-gray-400">Max Workers: 5</p>
                <p class="text-gray-400">Supervisor Model: gemini-2.0-flash-exp</p>
                <p class="text-gray-400">Worker Model: gemini-2.0-flash-exp</p>
            </div>

            <div>
                <h3 class="text-xl font-bold">Pricing</h3>
                <p class="text-gray-400">Starter: $19.99/mo</p>
                <p class="text-gray-400">Pro: $49.99/mo</p>
                <p class="text-gray-400">Enterprise: $199.99/mo</p>
            </div>
        </div>
    </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn

    print("🔐 Admin Panel Starting...")
    print("   URL: http://localhost:8400")
    print(f"   Username: {ADMIN_USERNAME}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print("")
    uvicorn.run(app, host="0.0.0.0", port=8400)
