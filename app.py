import os
import re
import time
import boto3
import redis
from slackclient import SlackClient
from aws_details import *
from utils import *


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path)

# instantiate Slack client
slack_token = os.environ['SLACK_TOKEN']
slack_client = SlackClient(slack_token)

# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "hello"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

# Redis details 
redis_host = "localhost"
redis_port = 7379 # Note : Redis running on port 7379
redis_password = ""


def connect_redis():
    try:
        redisClient = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)
        print("connection to redis successful") 
        return redisClient
    except Exception as e:
        print(e)
        return None


def check_duplicate_ip(user):
    sg = security_groups[-2]
    security_group = ec2.SecurityGroup(sg)

    ipv4_ranges = security_group.ip_permissions[0]['IpRanges']
    ipv6_ranges = security_group.ip_permissions[0]['Ipv6Ranges']
    names_in_ipv4 = [des['Description'] for des  in ipv4_ranges]
    values = names_in_ipv4.count(user)

    if len(ipv6_ranges) >= 1:
        names_in_ipv6 = [des['Description'] for des  in ipv6_ranges]
        ipv6_values = names_in_ipv6.count(user)
        values += ipv6_values

    if values <= 2:
        return None
    else:
        return values


def get_old_ip(user):
    sg = security_groups[-2]
    security_group = ec2.SecurityGroup(sg)
    
    try:
        ip_ranges = security_group.ip_permissions[0]['IpRanges']
        names = [des['Description'] for des  in ip_ranges]
        index = names.index(user)
        all_ips = [ip['CidrIp'] for ip  in ip_ranges]
        old_ip = all_ips[index]
        return old_ip
    except:
        ip_ranges = security_group.ip_permissions[0]['Ipv6Ranges']
        names = [des['Description'] for des  in ip_ranges]
        index = names.index(user)
        all_ips = [ip['CidrIpv6'] for ip  in ip_ranges]
        old_ip = all_ips[index]
        return old_ip


def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                user = event.get('user')
                return message, event["channel"], user
    return None, None, None


def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)


def handle_command(command, channel, user):
    """
        Executes bot command if the command is known
    """
    # get name of user based on id
    user_name = get_user_info(user)
    print(user_name)

    if command.lower().startswith('revoke'):
        get_ip = command.split("revoke ",1)[1]
        ip = validate_ip(get_ip)
    else:
        ip = validate_ip(command)

    user_mention = get_mention(user)

    # Default response is help text for the user
    default_response = "*{}* Not sure what you mean. Try *{}*.".format(user_mention,EXAMPLE_COMMAND)
    response = None

    if ip and not command.lower().startswith('revoke'):
        multi_ip = check_duplicate_ip(user_name)

    if command.lower().startswith(EXAMPLE_COMMAND) or command.lower().startswith('hi') or command.lower().startswith('hey'):
        response = "Hey *{}*  Thanks for your response. Please send your IP.".format(user_mention)
     
    elif ip and command.lower().startswith('revoke'):
        response = "Hey *{}*  Done.".format(user_mention)
        get_ip = command.split("revoke ",1)[1]
        ip_address = get_ip + "/32"


        for sg in security_groups:
            security_group = ec2.SecurityGroup(sg)
            try:
                if ip.version is 6:
                    remove_ip = security_group.revoke_ingress(GroupId=sg,IpPermissions=[ {'IpProtocol': '-1','FromPort': -1,'ToPort': -1,'Ipv6Ranges':[{'CidrIpv6': ip_address }]}])
                elif ip.version is 4:
                    remove_ip = security_group.revoke_ingress(GroupId=sg,IpPermissions=[ {'IpProtocol': '-1','FromPort': -1,'ToPort': -1,'IpRanges':[{'CidrIp': ip_address }]}])
                print('IP removed from security group %s' % sg)
            except Exception as e:
                print(e)
                pass
                
        print('%s removed from all security group' % ip_address)

        try:
            # Make connection to redis 
            db = connect_redis()
            db.delete(user_name)
            print("user data updated on redis database")
        except Exception as e:
            print(e)

    elif ip and multi_ip:
        old_ip = get_old_ip(user_name)

        ip_address = command + "/32"

        for sg in security_groups:
            security_group = ec2.SecurityGroup(sg)
            try:
                if ip.version is 6:
                    remove_ip = security_group.revoke_ingress(GroupId=sg,IpPermissions=[ {'IpProtocol': '-1','FromPort': -1,'ToPort': -1,'Ipv6Ranges':[{'CidrIpv6': old_ip }]}])
                    print('IP removed from security group %s' % sg)
                    add_ip = security_group.authorize_ingress(GroupId=sg,IpPermissions=[ {'IpProtocol': '-1','FromPort': -1,'ToPort': -1,'Ipv6Ranges':[{'CidrIpv6': ip_address, 'Description' : '{}'.format(user_name)}]}])
                    print('IP added in security group %s' % sg)
                elif ip.version is 4:
                    remove_ip = security_group.revoke_ingress(GroupId=sg,IpPermissions=[ {'IpProtocol': '-1','FromPort': -1,'ToPort': -1,'IpRanges':[{'CidrIp': old_ip }]}])
                    print('IP removed from security group %s' % sg)
                    add_ip = security_group.authorize_ingress(GroupId=sg,IpPermissions=[ {'IpProtocol': '-1','FromPort': -1,'ToPort': -1,'IpRanges':[{'CidrIp': ip_address, 'Description' : '{}'.format(user_name)}]}])
                    print('IP added in security group %s' % sg)

            except Exception as e:
                print(e)
                pass

        response = "Hey *{}*  I removed your old IP {} and added new IP {} :)".format(user_mention, old_ip, ip_address)

    elif ip:
        response = "Hey *{}*  Thanks.".format(user_mention)

        ip_address = command + "/32"
        for sg in security_groups:
            security_group = ec2.SecurityGroup(sg)
            try:
                if ip.version is 6:
                    add_ip = security_group.authorize_ingress(GroupId=sg,IpPermissions=[ {'IpProtocol': '-1','FromPort': -1,'ToPort': -1,'Ipv6Ranges':[{'CidrIpv6': ip_address, 'Description' : '{}'.format(user_name)}]}])

                elif ip.version is 4:
                    add_ip = security_group.authorize_ingress(GroupId=sg,IpPermissions=[ {'IpProtocol': '-1','FromPort': -1,'ToPort': -1,'IpRanges':[{'CidrIp': ip_address, 'Description' : '{}'.format(user_name)}]}])
                print('IP added in security group %s' % sg)
            except Exception as e:
                print(e)
                pass

        print('%s Added in all security group' % ip_address)
        
        try:
            # Make connection to redis 
            db = connect_redis()
            data = db.set(user_name, ip)
            if data:
                print("user data update on redis database")
        except Exception as e:
                print(e)

        
    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )


if __name__ == "__main__":

    # Make connection to slack_client
    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel, user = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel, user)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")

