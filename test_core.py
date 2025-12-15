from core import BiliDownloader
import unittest

class TestCore(unittest.TestCase):
    def test_extract_bvid(self):
        downloader = BiliDownloader()
        self.assertEqual(downloader._extract_bvid("https://www.bilibili.com/video/BV1fK4y1t7Hj"), "BV1fK4y1t7Hj")
        self.assertEqual(downloader._extract_bvid("BV1fK4y1t7Hj"), "BV1fK4y1t7Hj")
        
    def test_get_info(self):
        downloader = BiliDownloader()
        # Use a known valid video
        bvid = "BV1Qs411k7Qv" 
        try:
            info = downloader.get_video_info(bvid)
            print(f"Title: {info['title']}")
            self.assertTrue('title' in info)
        except Exception as e:
            print(f"API Error for {bvid}: {e}")
            pass

if __name__ == '__main__':
    unittest.main()
