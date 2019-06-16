import discord
import os, sys, re, json
import secrets

from tools import *
from ipupdater import get_ip_updated, get_ips, get_public_ip

class Config:
    def __init__(self):
        # Defaults
        self.run = True
        self.unsafe = False
    def configure(self, args):
        for arg in args:
            if re.match(r'--?d(ebug)?', arg) is not None:
                self.run = False
                # Print debug information
            if re.match(r'--?u(nsafe)?', arg) is not None:
                self.unsafe = True

def get_token_filename():
    return os.path.join(get_perms_folder_path(), 'token.txt')

def get_admin_filename():
    return os.path.join(get_perms_folder_path(), 'administrators.json')

# Get our token
with open(get_token_filename(), 'r') as file:
    token = file.read().strip(' \n\r')

client = discord.Client()
verification_list = {}
config = Config()

def print_confirmation_number(author, channel):
    global verification_list
    if len(verification_list) > 3:
        print("Not printing verification number; too many requests.")
        return
    gen = secrets.SystemRandom()
    vnum = gen.randint(1000000000000000, 9999999999999999)
    print("Verification number for username:", author.display_name, "is:",
        vnum)
    verification_list[author.id] = vnum

confirmation_list = {}
def print_generic_confirmation_number(author, kind):
    global confirmation_list
    if kind not in confirmation_list:
        confirmation_list[kind] = {}
    if author.id in confirmation_list[kind]:
        print('Refusing to create a second', kind, 'confirmation number for',
                author.display_name)
        return
    gen = secrets.SystemRandom()
    vnum = gen.randint(1000000000000000, 9999999999999999)
    print("Verification number for username:", author.display_name, "is:", vnum)
    confirmation_list[kind][author.id] = {'number': vnum, 'count': 0}

def is_confirmed_deleting(author, kind, confirmation_number):
    global confirmation_list
    if kind not in confirmation_list:
        return False
    if author.id not in confirmation_list[kind]:
        return False
    if confirmation_list[kind][author.id]['number'] != confirmation_number:
        confirmation_list[kind][author.id]['count'] += 1
        return False
    del confirmation_list[kind][author.id]
    return True

def is_administrator(message=None, id=None, verbose=False):
    admins = safe_load_json(get_admin_filename())

    # Input sanitization
    identifier = id
    if message is not None:
        identifier = message.author.id
    identifier = int(identifier)

    if verbose:
        for i in admins['user-ids']:
            print(i, identifier, i==identifier)

    return 'user-ids' in admins and identifier in admins['user-ids'] 
    # "botadministrator" in [role.name.lower() for role in message.author.roles]

def direct_add_administrator(user_id):
    admins = safe_load_json(get_admin_filename()) 
    # Lookup table
    if 'user-ids' not in admins:
        admins['user-ids'] = []
    if user_id not in admins['user-ids']:
        admins['user-ids'].append(user_id)
    with open(get_admin_filename(), 'w') as file:
        json.dump(admins, file, indent=2)

def set_administrator(verification_num, message):
    if not config.unsafe:
        return 
    if message.author.id in verification_list and verification_list[message.author.id] == verification_num:
        print("Making user verifified:", message.author.display_name)
    else:
        return
    direct_add_administrator(message.author.id)

async def del_message(message):
    try:
        await message.delete()
    except discord.Forbidden:
        print("Warning: No permissions to delete messages.")
    except discord.HTTPException:
        print("Warning: Deleting a message failed.")

def get_server_status(ip):
    from mcstatus import MinecraftServer
    server = MinecraftServer.lookup(ip)
    try:
        status = server.status()
        return status
    except ConnectionRefusedError:
        return None

def get_server_status_as_str(ip):
    status = get_server_status(ip)
    if status is None:
        return "The server is currently down."
    return "The server is currently up, with {0} users connected. ({1}ms response time)".format(status.players.online, status.latency)

def get_help():
    return """
`~status`\t\tGet the server's status.
`~ip`\t\t\t\tGet the server's IP address.
"""

@client.event
async def on_message(message):
    # Basic guard for the bot messages
    if message.author == client.user:
        return

    channel = message.channel

    mcl = message.content.lower().strip(' \r\n')
    if is_administrator(message):
        # Allowed to administrate the bot
        # We run through these commands first
        cmd = message.content
        if re.match(r'~stop', cmd):
            await client.logout()
            return
        don = re.match(r'~don <?@?!?([0-9]+)>?', cmd)
        if don is not None:
            don = don.group(1)
            print('Adding administrator:', don)
            direct_add_administrator(int(don))
            return
        ec = re.match(r"~echo ([\s\S]+)", message.content)
        if ec is not None:
            await channel.send(ec.group(1))
            return
        if re.match(r"~ip", message.content.lower()) is not None:
            newip = get_ip_updated()
            if newip is not None:
                await channel.send('New IP: `' + newip + '`')
            else:
                await channel.send('IP is unchanged.')
            return
        if re.match(r"~status", mcl) is not None:
            await channel.send(get_server_status_as_str(get_ips().private))
            return

        if cmd.startswith('~'):
            print('Could not understand command (as admin):', cmd)

    if re.match(r"~help", mcl) is not None:
        await channel.send(get_help())
        return

    if re.match(r"hey vsauce,?", mcl) is not None:
        await channel.send("Michael here!")
        return
    if re.match(r"~req_verify", mcl) is not None:
        await del_message(message)
        print_confirmation_number(message.author, channel.guild.id)
        return
    vn = re.match(r"~verify ?([0-9]+)", mcl)  
    if vn is not None:
        await del_message(message)
        vn = int(vn.group(1))
        print("Received confirmation number:", vn)
        set_administrator(vn, message) 
        return

    if re.match(r"~help", mcl):
        await channel.send("No help for you!")
        return

    if re.match(r"~!db:uid$", mcl):
        print("User-ID:", message.author.id)
        return
    if re.match(r"~!db:isadmin$", mcl):
        print("User-ID:", message.author.id)
        print("Is Administrator:", is_administrator(message=message, verbose=True))
        return

    if re.match(r"~!db:stop$", mcl):
        print_generic_confirmation_number(author=message.author, kind="stop-bot")
        return
    vn = re.match(r"~!db-exe:stop ?([0-9]+)$", mcl)  
    if vn is not None:
        if is_confirmed_deleting(message.author, "stop-bot", int(vn.group(1))):
            await client.logout()
            return

    # await channel.send(message.content)

@client.event
async def on_ready():
    print('Logged in as:')
    print(client.user.name)
    print(client.user.id)
    print('-------')

    # Clean up some information
    admins = safe_load_json(get_admin_filename()) 
    if 'user-ids' not in admins:
        return
    for x in range(0, len(admins['user-ids'])):
        try:
            admins['user-ids'][x] = int(admins['user-ids'][x])
        except ValueError:
            print('The user-id of', uid, 'in the administrators file could not be converted to an integer.')
    with open(get_admin_filename(), 'w') as file:
        json.dump(admins, file, indent=2)

if __name__ == '__main__':
    args = sys.argv[1:]
    config.configure(args)

    if not config.run:
        sys.exit()

    client.run(token)

