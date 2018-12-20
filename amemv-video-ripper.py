# -*- coding: utf-8 -*-

import os
import sys
import urllib.parse
import urllib.request
import copy
import hashlib
import requests
import re
from six.moves import queue as Queue
from threading import Thread
import json
import time

"""
添加MAX_VIDEOS变量控制下载视频个数
"""
# Setting max number of videos
MAX_VIDEOS = 20

# Setting timeout
TIMEOUT = 10

# Retry times
RETRY = 5

# Numbers of downloading threads concurrently
THREADS = 10

HEADERS = {
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'zh-CN,zh;q=0.9',
    'pragma': 'no-cache',
    'cache-control': 'no-cache',
    'upgrade-insecure-requests': '1',
    'user-agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1",
}


def getRemoteFileSize(url, proxy=None):
    '''
    通过content-length头获取远程文件大小
    '''
    try:
        request = urllib.request.Request(url)
        request.get_method = lambda: 'HEAD'
        response = urllib.request.urlopen(request)
        response.read()
    except urllib.error.HTTPError as e:
        # 远程文件不存在
        print(e.code)
        print(e.read().decode("utf8"))
        return 0
    else:
        fileSize = dict(response.headers).get('Content-Length', 0)
        return int(fileSize)


def download(medium_type, uri, medium_url, target_folder):
    headers = copy.copy(HEADERS)
    file_name = uri
    if medium_type == 'video':
        file_name += '.mp4'
        headers['user-agent'] = 'Aweme/27014 CFNetwork/974.2.1 Darwin/18.0.0'
    elif medium_type == 'image':
        file_name += '.jpg'
        file_name = file_name.replace("/", "-")
    else:
        return

    file_path = os.path.join(target_folder, file_name)
    if os.path.isfile(file_path):
        remoteSize = getRemoteFileSize(medium_url)
        localSize = os.path.getsize(file_path)
        if remoteSize == localSize:
            return
    print("Downloading %s from %s.\n" % (file_name, medium_url))
    retry_times = 0
    while retry_times < RETRY:
        try:
            resp = requests.get(medium_url, headers=headers, stream=True, timeout=TIMEOUT)
            if resp.status_code == 403:
                retry_times = RETRY
                print("Access Denied when retrieve %s.\n" % medium_url)
                raise Exception("Access Denied")
            with open(file_path, 'wb') as fh:
                for chunk in resp.iter_content(chunk_size=1024):
                    fh.write(chunk)
            break
        except:
            pass
        retry_times += 1
    else:
        try:
            os.remove(file_path)
        except OSError:
            pass
        print("Failed to retrieve %s from %s.\n" % medium_url)
    time.sleep(1)


# challenge id to url
def get_challenge_url(c_id):
    base_url = "https://www.iesdouyin.com/share/challenge/"
    return base_url + str(c_id)


def get_dytk(url):
    res = requests.get(url, headers=HEADERS)
    if not res: return None
    dytk = re.findall("dytk: '(.*)'", res.content.decode('utf-8'))
    if len(dytk): return dytk[0]
    return None


class DownloadWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            medium_type, uri, download_url, target_folder = self.queue.get()
            download(medium_type, uri, download_url, target_folder)
            self.queue.task_done()


class CrawlerScheduler(object):

    def __init__(self, items, tags):
        # self.numbers = []
        self.challenges = []
        # self.musics = []
        self.tags = tags
        for i in range(len(items)):
            # url = get_real_address(items[i])  # 处理短网址
            url = get_challenge_url(items[i])
            # if not url:
            #     continue
            # if re.search('share/user', url):  # 处理用户视频
            #    self.numbers.append(url)
            # if re.search('share/challenge', url):  # 处理话题
            self.challenges.append(url)
            # if re.search('share/music', url):  # 处理音乐
            #    self.musics.append(url)

        self.queue = Queue.Queue()
        self.scheduling()

    @staticmethod
    def generateSignature(value):
        p = os.popen('/usr/local/bin/node fuck-byted-acrawler.js %s' % value)
        return p.readlines()[0]

    @staticmethod
    def calculateFileMd5(filename):
        hmd5 = hashlib.md5()
        fp = open(filename, "rb")
        hmd5.update(fp.read())
        return hmd5.hexdigest()

    def scheduling(self):
        for x in range(THREADS):
            worker = DownloadWorker(self.queue)
            worker.daemon = True
            worker.start()

        for url in self.challenges:
            self.download_challenge_videos(url)

    def download_challenge_videos(self, url):
        challenge = re.findall('share/challenge/(\d+)', url)
        if not len(challenge):
            return
        challenges_id = challenge[0]
        video_count = self._download_challenge_media(challenges_id, url)
        self.queue.join()
        print("\nAweme challenge #%s, video number %d\n\n" % (challenges_id, video_count))
        print("\nFinish Downloading All the videos from #%s\n\n" % challenges_id)

    def _join_download_queue(self, aweme, target_folder):
        try:
            if aweme.get('video', None):
                uri = aweme['video']['play_addr']['uri']
                download_url = "https://aweme.snssdk.com/aweme/v1/play/?{0}"
                download_params = {
                    'video_id': uri,
                    'line': '0',
                    'ratio': '720p',
                    'media_type': '4',
                    'vr_type': '0',
                    'test_cdn': 'None',
                    'improve_bitrate': '0',
                    'iid': '35628056608',
                    'device_id': '46166618999',
                    'os_api': '18',
                    'app_name': 'aweme',
                    'channel': 'App%20Store',
                    'idfa': '00000000-0000-0000-0000-000000000000',
                    'device_platform': 'iphone',
                    'build_number': '27014',
                    'vid': '2ED380A7-F09C-6C9E-90F5-862D58F3129C',
                    'openudid': '21dae85eeac1da35a69e2a0ffeaeef61c78a2e98',
                    'device_type': 'iPhone8%2C2',
                    'app_version': '2.7.0',
                    'version_code': '2.7.0',
                    'os_version': '12.0',
                    'screen_width': '1242',
                    'aid': '1128',
                    'ac': 'WIFI'
                }
                if aweme.get('hostname') == 't.tiktok.com':
                    download_url = 'http://api.tiktokv.com/aweme/v1/play/?{0}'
                    download_params = {
                        'video_id': uri,
                        'line': '0',
                        'ratio': '720p',
                        'media_type': '4',
                        'vr_type': '0',
                        'test_cdn': 'None',
                        'improve_bitrate': '0',
                        'version_code': '1.7.2',
                        'language': 'en',
                        'app_name': 'trill',
                        'vid': 'D7B3981F-DD46-45A1-A97E-428B90096C3E',
                        'app_version': '1.7.2',
                        'device_id': '6619780206485964289',
                        'channel': 'App Store',
                        'mcc_mnc': '',
                        'tz_offset': '28800'
                    }
                url = download_url.format('&'.join([key + '=' + download_params[key] for key in download_params]))
                self.queue.put(('video', uri, url, target_folder))
            else:
                if aweme.get('image_infos', None):
                    image = aweme['image_infos']['label_large']
                    self.queue.put(('image', image['uri'], image['url_list'][0], target_folder))

        except KeyError:
            return
        except UnicodeDecodeError:
            print("Cannot decode response data from DESC %s" % aweme['desc'])
            return

    def _download_challenge_media(self, challenge_id, url):
        if not challenge_id:
            print("Challenge #%s does not exist" % challenge_id)
            return
        current_folder = os.getcwd()
        tag = self.tags.get(challenge_id)
        target_folder = os.path.join(current_folder, 'download/%s_%s' % (tag, challenge_id))
        if not os.path.isdir(target_folder):
            os.mkdir(target_folder)

        hostname = urllib.parse.urlparse(url).hostname
        signature = self.generateSignature(str(challenge_id) + '9' + '0')

        challenge_video_url = "https://%s/aweme/v1/challenge/aweme/" % hostname
        challenge_video_params = {
            'ch_id': str(challenge_id),
            'count': '9',  # 每次请求获取的视频个数 #
            'cursor': '0',
            'aid': '1128',
            'screen_limit': '3',
            'download_click_limit': '0',
            '_signature': signature
        }

        cursor, video_count = None, 0
        while True:
            if cursor:
                challenge_video_params['cursor'] = str(cursor)
                challenge_video_params['_signature'] = self.generateSignature(str(challenge_id) + '9' + str(cursor))
            res = requests.get(challenge_video_url, headers=HEADERS, params=challenge_video_params)
            try:
                contentJson = json.loads(res.content.decode('utf-8'))
            except:
                print(res.content)
            aweme_list = contentJson.get('aweme_list', [])
            if not aweme_list:
                break
            for aweme in aweme_list:
                aweme['hostname'] = hostname
                video_count += 1
                self._join_download_queue(aweme, target_folder)
                print("number: ", video_count)
            if contentJson.get('has_more'):
                """
                添加MAX_VIDEOS控制下载视频的个数
                """
                if video_count < MAX_VIDEOS:
                    cursor = contentJson.get('cursor')
                else:
                    print("视频个数达到MAX_VIDEOS，停止获取URL！！！")
                    break
            else:
                print("该分类下没有更多了的视频了！！！")
                break
        if video_count == 0:
            print("There's no video in challenge %s." % challenge_id)
        return video_count


def usage():
    print(u"编辑tag-url.json文件.\n"
          u"要求每个item具有tag和cid两个字段:\n"
          u"例如：tag: 风景, cid: 1562172675762177 ...\n")


def parse_sites(fileName):
    tags = dict()
    c_ids = list()
    with open(fileName, "rb") as f:
        _data = json.load(f)
        data = _data['tags_urls_list']
        for item in data:
            c_id = str(item['cid'])
            tag = str(item['tag'])
            tags[c_id] = tag
            c_ids.append(c_id)
    return tags, c_ids


noFavorite = False

if __name__ == "__main__":
    content, opts, args = None, None, []

    # check the sites file
    filename = "tag-url.json"
    if os.path.exists(filename):
        Tags, C_ids = parse_sites(filename)
    else:
        usage()
        sys.exit(1)

    CrawlerScheduler(C_ids, Tags)
