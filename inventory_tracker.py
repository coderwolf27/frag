import asyncio
import glob
import os
import aiohttp
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import GetAdminedPublicChannelsRequest
from telethon.tl.functions.account import UpdateProfileRequest

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

API_ID = 24253078
API_HASH = "127ce5bd1d3d87bfc31770a40f85f3c1"

async def is_on_auction(username):
    url = f"https://fragment.com/username/{username}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=True) as resp:
            final_url = str(resp.url)
            if "?query=" in final_url:
                return False
            html = await resp.text()
            if "tm-status-auction" in html or "Ends in" in html or "Current bid" in html or "Sold for" in html:
                return True
            return False

async def check_account(session_file):
    client = TelegramClient(session_file, API_ID, API_HASH)
    try:
        await client.start(max_attempts=3)
    except Exception as e:
        error_msg = str(e).lower()
        if "database is locked" in error_msg:
            print(f"\n⚠️ SESSION LOCKED: '{session_file}' is currently being used by another running script (like PM2 or your checker).")
            print(f"   You must stop the other script if you want to scan this account. Skipping...")
        else:
            print(f"\n❌ Login failed (Wrong password or invalid session): {e}")
            session_path = f"{session_file}.session"
            if os.path.exists(session_path):
                try:
                    os.remove(session_path)
                    print(f"🗑️ Removed broken session file: {session_path}")
                except:
                    pass
                    
        # Safely attempt disconnect without crashing if DB is locked
        try:
            await client.disconnect()
        except Exception:
            pass
            
        return

    me = await client.get_me()
    
    while True:
        print(f"\n=============================================")
        print(f"👤 Logged in as: {me.first_name} (+{me.phone})")
        
        request = GetAdminedPublicChannelsRequest(by_location=False, check_limit=False)
        result = await client(request)
        
        public_usernames = []
        for chat in result.chats:
            if chat.username:
                public_usernames.append(chat.username)
                
        print(f"Total public channel slots used: {len(public_usernames)}/10")
        
        # Tag full accounts visually
        if len(public_usernames) >= 10:
            current_name = me.first_name or ""
            current_last = me.last_name or ""
            if "❤️" not in current_name and "❤️" not in current_last:
                try:
                    new_first_name = current_name + " ❤️"
                    await client(UpdateProfileRequest(first_name=new_first_name))
                    print(f"  ❤️ Account is FULL! Automatically added ❤️ to Telegram profile name.")
                    # Update local 'me' object so we don't spam it next loop
                    me.first_name = new_first_name
                except Exception as e:
                    print(f"  ⚠️ Could not update profile name: {e}")
                    
        idle_usernames = []
        if public_usernames:
            print("\nChecking Fragment status for owned names...")
            for username in public_usernames:
                print(f"  🔍 Checking @{username}...")
                on_auction = await is_on_auction(username)
                if on_auction:
                    print(f"    -> 🏷️ Skipping (Currently on Auction/Sold)")
                else:
                    print(f"    -> 🟢 IDLE (Not on auction, ready to sell/mint)")
                    idle_usernames.append(username)
        else:
            print("  -> No public channels found on this account.")
                
        print(f"\n📊 SUMMARY FOR +{me.phone}:")
        print(f"Slots Used:  {len(public_usernames)} / 10")
        print(f"Slots Empty: {10 - len(public_usernames)} / 10")
        print(f"Idle/Unlisted Usernames: {', '.join(idle_usernames) if idle_usernames else 'None'}")
        print(f"=============================================\n")
        
        choice = input("[?] Type 'r' to RESCAN this account, or press ENTER to delete session and continue: ").strip().lower()
        if choice != 'r':
            break
    
    await client.disconnect()
    
    session_path = f"{session_file}.session"
    if os.path.exists(session_path):
        try:
            os.remove(session_path)
            print(f"🗑️ Removed session file: {session_path}")
        except Exception as e:
            print(f"⚠️ Could not remove session file: {e}")

async def main():
    sessions = glob.glob("*.session")
    sessions = [s for s in sessions if "bot_ui" not in s and "adbot" not in s and "checker_session" not in s]
    
    if not sessions:
        print("No user accounts found. Let's log in to your first one.")
        session_name = input("Enter a name for this account (e.g., account1): ")
        await check_account(session_name)
    else:
        print(f"Found {len(sessions)} saved accounts! Scanning...")
        for s in sessions:
            session_name = s.replace('.session', '')
            await check_account(session_name)
            
        print("\nScan complete!")

if __name__ == "__main__":
    asyncio.run(main())
