# bruhbot repo

This is an awfully written bot for experimenting, nothing to see here. It's a personal project that I doubt you would
wanna use, but who knows.

It needs a config file called "bot-config.toml"

Example:

```toml
use_bridge_regex=true # whether to check for usernames from the bridge or not
bridge_regex = '''^\[\w+/\w+\]\s<(.+?)>\s{1}''' # so that it knows what usernames to use from the bridge
bridge_bot_name = "bridgyboi" # the name of the bot that the bridge uses
channel="#botest" # for the irc server
bot_name="bruhbot" # the name of this bot
tls_verify=true # for the irc server
tls=true # for the irc server
password="ifany" # for the irc server
host="whatever.com" # for the irc server
port="6697" # for the irc server
only_bridge=false # if it should accept commands from the bridge only
debug=false # if this is true, it will allow anyone to use the bridge pattern to impersonate an user
sasl_identify=false # if the bot is registered (you also need to install the pure-sasl module)
sasl_username="bruhbot"
sasl_password="blahblah"
sasl_mechanism="PLAIN"
```

It's a good idea to make a second commands file called "local-commands.toml" 
if you wanna customize your commands, so that you don't accidentally commit the changes. 
If the file doesn't exist, the script will use the main one. If you want to make a fork 
of this project and customize, then use the main commands file.

Info for regex: https://docs.python.org/3/library/re.html

For the pports command you can create a config file "ping_config.toml":

```toml
[port.http]
number = 80

[port.https]
number = 443
```

add whatever port names and numbers you wish to.