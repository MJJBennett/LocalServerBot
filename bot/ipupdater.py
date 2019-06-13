from urllib.request import urlopen
import json, socket, time
from tools import *

class IPInfo:
    def __init__(self, privateip, publicip, ip=None):
        self.private = privateip
        self.public = publicip
        self.ip = ip

def get_ip_path():
    return os.path.join(get_perms_folder_path(), 'ipinfo.json')

def get_public_ip():
    public_ip = urlopen('http://ip.42.pl/raw').read().decode("utf-8")
    return IPInfo(privateip=None, publicip=public_ip, ip=public_ip)

def get_ips():
    localip = socket.gethostbyname_ex(socket.gethostname())[2][1]
    publicip = get_public_ip().ip
    return IPInfo(localip, publicip)

def save(ip):
    with open(get_ip_path(), 'w') as file:
        json.dump({'old-private': ip.private, 'old-public': ip.public}, file, indent=2)

def get_ip_updated():
    prev = safe_load_json(get_ip_path())
    ip = get_ips()
    save(ip)

    if 'old-private' in prev and prev['old-private'] == ip.private:
        # No change
        pass
    else:
        print('Private IP changed, new:', ip.private)

    if 'old-public' in prev and prev['old-public'] == ip.public:
        # No change
        return None
    else:
        return ip.public

