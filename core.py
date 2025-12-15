import requests
import re
import os
import subprocess
import time
import qrcode
import pickle
from io import BytesIO

class BiliAuthenticator:
    def __init__(self, session):
        self.session = session
        self.qrcode_key = None
        
    def get_login_qrcode(self):
        """Get QR code url and key"""
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
        response = self.session.get(url)
        data = response.json()
        if data['code'] == 0:
            self.qrcode_key = data['data']['qrcode_key']
            return data['data']['url']
        raise Exception("Failed to generate QR code")

    def get_qrcode_image(self, url):
        """Generate QR code image from URL"""
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def poll_login_status(self):
        """
        Check login status
        Returns: 
            (status_code, message/cookie_info)
            0: Success
            86101: Waiting for scan
            86090: Scanned, waiting for confirm
            86038: Expired
        """
        if not self.qrcode_key:
            raise Exception("No QR code key")
            
        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={self.qrcode_key}"
        response = self.session.get(url)
        data = response.json()
        
        if data['code'] == 0:
            code = data['data']['code']
            if code == 0:
                # Login success, cookies are already in session
                return 0, "Login Success"
            return code, data['data']['message']
        return -1, "Unknown Error"

class BiliDownloader:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.authenticator = BiliAuthenticator(self.session)
        self.cookie_file = "cookies.pkl"
        self.load_cookies()

    def save_cookies(self):
        try:
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(self.session.cookies, f)
        except Exception as e:
            print(f"Failed to save cookies: {e}")

    def load_cookies(self):
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'rb') as f:
                    self.session.cookies.update(pickle.load(f))
            except Exception as e:
                print(f"Failed to load cookies: {e}")

    def logout(self):
        """Logout by clearing cookies"""
        self.session.cookies.clear()
        if os.path.exists(self.cookie_file):
            try:
                os.remove(self.cookie_file)
            except Exception as e:
                print(f"Failed to delete cookie file: {e}")

    def get_user_info(self):
        """Get logged in user info (nav endpoint)"""
        url = "https://api.bilibili.com/x/web-interface/nav"
        try:
            response = self.session.get(url)
            data = response.json()
            if data['code'] == 0:
                if data['data']['isLogin']:
                    return data['data']
            return None
        except:
            return None

    def get_video_info(self, url_or_bvid):
        bvid = self._extract_bvid(url_or_bvid)
        if not bvid:
            raise ValueError("Invalid URL or BVID")
        
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        response = self.session.get(api_url)
        data = response.json()
        
        if data['code'] != 0:
            raise Exception(f"API Error: {data['message']}")
            
        return data['data']

    def get_play_url(self, bvid, cid, qn=80):
        # qn: 127=8K, 120=4K, 116=1080P60, 80=1080P, 64=720P
        # fnval=4048 (4K)
        api_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={qn}&fnval=4048&fourk=1"
        response = self.session.get(api_url)
        data = response.json()
        
        if data['code'] != 0:
            raise Exception(f"API Error: {data['message']}")
            
        # Filter logic for DASH to ensure we get the requested quality
        if 'dash' in data['data']:
            # Find best matching video stream for requested qn
            # or simply return all data and let GUI decide, but here we update logic
            pass
            
        return data['data']

    def _extract_bvid(self, text):
        match = re.search(r'(BV\w+)', text)
        if match:
            return match.group(1)
        return text if text.startswith('BV') else None

    def download_file(self, url, filepath, progress_callback=None):
        response = self.session.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        wrote = 0
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            for data in response.iter_content(block_size):
                wrote += len(data)
                f.write(data)
                if progress_callback and total_size > 0:
                    progress_callback(wrote, total_size)

    def merge_video_audio(self, video_path, audio_path, output_path):
        """Merges video and audio using ffmpeg."""
        cmd = [
            'ffmpeg', '-y', # Overwrite output
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            output_path
        ]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

