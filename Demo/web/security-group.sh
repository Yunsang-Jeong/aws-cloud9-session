# Get the ID of the instance for the environment, and store it temporarily.
MY_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id) 

# Get the ID of the security group associated with the instance, and store it temporarily.
MY_SECURITY_GROUP_ID=$(aws ec2 describe-instances --instance-id $MY_INSTANCE_ID --query 'Reservations[].Instances[0].SecurityGroups[0].GroupId' --output text)

aws ec2 authorize-security-group-ingress --group-id $MY_SECURITY_GROUP_ID --protocol tcp --cidr 0.0.0.0/0 --port 8080