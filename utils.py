import ipaddress
from app import slack_client


# how the bot is mentioned on slack
def get_mention(user):
    return '<@{user}>'.format(user=user)


def get_user_info(user):
    user_name = slack_client.api_call("users.info", user=user).get('user', {}).get('name')
    return user_name


def validate_ip(ip):
    try:
        ipv4 = ipaddress.ip_address(ip)
        return ipv4
    except:
        return None

