
### SlackBot 

### Working 

To add IP in security groups :
@chatops-bot <your ip>

i.e. : @chatops-bot 127.1.1.1

To revoke IP :
@chatops-bot revoke <your ip>

i.e. : @chatops-bot revoke 127.1.1.1

Note :
1. Please remove old IP before adding new one
2. Allow only 3 IPs per user .

### Tech stack :

1. Python3.x 
2. slackclient
3. boto3
4. slackApi 
5. Docker

### References :

slack-api : https://api.slack.com
slack-client : https://github.com/slackapi/python-slackclient


###Infra details :

> docker build -t slackbot-prod:0.0.1 .

> docker-compose up -d
