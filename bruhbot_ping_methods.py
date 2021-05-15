from socket import gethostbyname, gaierror, create_connection
from re import search


async def ping_filtered(bot, hostname, target, unknown_port_msg):
    try:
        regex = search(r'192\.168.*', hostname)
    except TypeError:
        await bot.message(target, unknown_port_msg)
    else:
        if regex:
            await bot.message(target, unknown_port_msg)
            return True

    if hostname == "localhost":
        await bot.message(target, unknown_port_msg)
        return True

    if hostname == "127.0.0.1":
        await bot.message(target, unknown_port_msg)
        return True
    return False


async def connection_to_host(self, target, hostname, unknown_port_msg, got_port, print_hostname):
    try:
        got_host = gethostbyname(hostname)
    except gaierror:
        await self.message(target, unknown_port_msg)
        return False

    try:
        s = create_connection(address=(got_host, got_port), timeout=5)
        s.close()
        await self.message(target, f"{print_hostname} UP")
    except OSError:
        await self.message(target, f"{print_hostname} DOWN")
        return False

    return True
