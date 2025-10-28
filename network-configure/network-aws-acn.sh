### 1. Info VPC

aws ec2 describe-vpcs \
  --vpc-ids vpc-0c136d8bfa16fefe2 \
  --query 'Vpcs[0].{VpcId:VpcId,Cidr:CidrBlock,IsDefault:IsDefault,DhcpOptionsId:DhcpOptionsId,Tags:Tags}' \
  --output table

---------------------------------------------------------------------------------------------------------------------------------------------------
|                                                                  DescribeVpcs                                                                   |
+------------------------------+-----------------------------------+--------------------------+---------------------------------------------------+
|             Cidr             |           DhcpOptionsId           |        IsDefault         |                       VpcId                       |
+------------------------------+-----------------------------------+--------------------------+---------------------------------------------------+
|  10.1.0.0/16                 |  dopt-c37a54a5                    |  False                   |  vpc-0c136d8bfa16fefe2                            |
+------------------------------+-----------------------------------+--------------------------+---------------------------------------------------+
||                                                                     Tags                                                                      ||
|+-------------------------------+---------------------------------------------------------------------------------------------------------------+|
||              Key              |                                                     Value                                                     ||
|+-------------------------------+---------------------------------------------------------------------------------------------------------------+|
||  aws:cloudformation:stack-name|  VPNLiquidBackbone                                                                                            ||
||  Stack                        |  VPNLiquidBackbone                                                                                            ||
||  Application                  |  arn:aws:cloudformation:eu-west-1:055287546249:stack/VPNLiquidBackbone/a8039600-bb70-11ea-a7cf-06ebe7208a7c   ||
||  aws:cloudformation:logical-id|  VPC                                                                                                          ||
||  aws:cloudformation:stack-id  |  arn:aws:cloudformation:eu-west-1:055287546249:stack/VPNLiquidBackbone/a8039600-bb70-11ea-a7cf-06ebe7208a7c   ||
||  Name                         |  VPNLiquidBackbone-PCS-VPC                                                                                    ||
|+-------------------------------+---------------------------------------------------------------------------------------------------------------+|
### 2. Attributi DNS del VPC

aws ec2 describe-vpc-attribute --vpc-id vpc-0c136d8bfa16fefe2 --attribute enableDnsSupport
{
    "EnableDnsSupport": {
        "Value": true
    },
    "VpcId": "vpc-0c136d8bfa16fefe2"
}
aws ec2 describe-vpc-attribute --vpc-id vpc-0c136d8bfa16fefe2 --attribute enableDnsHostnames
{
    "EnableDnsHostnames": {
        "Value": true
    },
    "VpcId": "vpc-0c136d8bfa16fefe2"
}

### 3. Info Subnet

aws ec2 describe-subnets \
  --subnet-ids subnet-0ee6b6844590a943c \
  --query 'Subnets[0].{SubnetId:SubnetId,Cidr:CidrBlock,AZ:AvailabilityZone,MapPublicIpOnLaunch:MapPublicIpOnLaunch,Tags:Tags}' \
  --output table

---------------------------------------------------------------------------------------------------------------------------------------------------
|                                                                 DescribeSubnets                                                                 |
+-----------------------+----------------------------+-----------------------------------------+--------------------------------------------------+
|          AZ           |           Cidr             |           MapPublicIpOnLaunch           |                    SubnetId                      |
+-----------------------+----------------------------+-----------------------------------------+--------------------------------------------------+
|  eu-west-1a           |  10.1.0.16/28              |  False                                  |  subnet-0ee6b6844590a943c                        |
+-----------------------+----------------------------+-----------------------------------------+--------------------------------------------------+
||                                                                     Tags                                                                      ||
|+-------------------------------+---------------------------------------------------------------------------------------------------------------+|
||              Key              |                                                     Value                                                     ||
|+-------------------------------+---------------------------------------------------------------------------------------------------------------+|
||  aws:cloudformation:logical-id|  ExtSubnet                                                                                                    ||
||  aws:cloudformation:stack-id  |  arn:aws:cloudformation:eu-west-1:055287546249:stack/VPNLiquidBackbone/a8039600-bb70-11ea-a7cf-06ebe7208a7c   ||
||  Name                         |  VPNLiquidBackbone-PCS-ExtSubnet                                                                              ||
||  Stack                        |  VPNLiquidBackbone                                                                                            ||
||  aws:cloudformation:stack-name|  VPNLiquidBackbone                                                                                            ||
||  Application                  |  arn:aws:cloudformation:eu-west-1:055287546249:stack/VPNLiquidBackbone/a8039600-bb70-11ea-a7cf-06ebe7208a7c   ||
|+-------------------------------+---------------------------------------------------------------------------------------------------------------+|
### 4. Internet Gateway associato

aws ec2 describe-internet-gateways \
  --filters "Name=attachment.vpc-id,Values=vpc-0c136d8bfa16fefe2" \
  --query 'InternetGateways[*].InternetGatewayId' \
  --output table

---------------------------
|DescribeInternetGateways |
+-------------------------+
|  igw-068455da03f7a537a  |
+-------------------------+
### 5. Route Table associata alla subnet

aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values=subnet-0ee6b6844590a943c" \
  --query 'RouteTables[*].{RouteTableId:RouteTableId,Routes:Routes,Tags:Tags}' \
  --output table

### 6. Security Groups nel VPC

aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=vpc-0c136d8bfa16fefe2" \
  --query 'SecurityGroups[*].{GroupId:GroupId,Name:GroupName,Desc:Description}' \
  --output table

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
|                                                                                                                                                      DescribeSecurityGroups                                                                                                                                                       |
+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+-----------------------+----------------------------------------------------------------------------------------------------+
|                                                                                                 Desc                                                                                                 |        GroupId        |                                               Name                                                 |
+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+-----------------------+----------------------------------------------------------------------------------------------------+
|  launch-wizard-5 created 2023-12-18T14:28:13.912Z                                                                                                                                                    |  sg-0c961b6be8760f7c5 |  launch-wizard-5                                                                                   |
|  launch-wizard-4 created 2020-07-08T10:24:42.292+02:00                                                                                                                                               |  sg-0da96193ffc12d846 |  launch-wizard-4                                                                                   |
|  Security group attached to instances to securely connect to nft-database. Modification could lead to connection loss.                                                                               |  sg-0e26298a9f4f9911a |  ec2-rds-1                                                                                         |
|  Security group attached to test-tamietti to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss.                      |  sg-0d82d0252b1fced52 |  rds-ec2-9                                                                                         |
|  default VPC security group                                                                                                                                                                          |  sg-047d1dcd3e4659522 |  default                                                                                           |
|  launch-wizard-8 created 2020-11-25T22:33:03.388+01:00                                                                                                                                               |  sg-04b77d3d486c7b5c8 |  launch-wizard-8                                                                                   |
|  launch-wizard-8 created 2020-09-02T09:44:41.805+02:00                                                                                                                                               |  sg-0a0a1f8f84b186633 |  gse_corda_machine                                                                                 |
|  Security group attached to instances to securely connect to acin-digital-certificate. Modification could lead to connection loss.                                                                   |  sg-06cbf6c318cc99318 |  ec2-rds-5                                                                                         |
|  launch-wizard-2 created 2020-07-07T18:46:28.004+02:00                                                                                                                                               |  sg-020982a5633764c38 |  launch-wizard-2                                                                                   |
|  Security group attached to algorand-multisig-test-scalability to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss. |  sg-0707d36fa1bb4e811 |  rds-ec2-7                                                                                         |
|  Security group for AWS Cloud9 environment aws-cloud9-basic-environment-4c36d31da1a741dc9efb3a9131f8cb4a                                                                                             |  sg-05140be570c7fb5e1 |  aws-cloud9-basic-environment-4c36d31da1a741dc9efb3a9131f8cb4a-InstanceSecurityGroup-QKK2Y72TL4U4  |
|  alloea access to efs                                                                                                                                                                                |  sg-0507aff76752cc733 |  efs-mount-sg                                                                                      |
|  std-security-group                                                                                                                                                                                  |  sg-0a801c5aad035e43d |  comunitaenergetichesecuritygroup                                                                  |
|  Security group attached to acin-digital-certificate to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss.           |  sg-0ab4e56ef9ffc975e |  rds-ec2-5                                                                                         |
|  Security group attached to nft-database to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss.                       |  sg-0ea31ab24b3974102 |  rds-ec2-2                                                                                         |
|  Security group attached to algorand-multisig-scalability to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss.      |  sg-0927c0740319af22f |  rds-ec2-6                                                                                         |
|  Security group attached to instances to securely connect to algorand-multisig-scalability. Modification could lead to connection loss.                                                              |  sg-0faeeef3f2ae143cb |  ec2-rds-6                                                                                         |
|  Security group attached to algo-indexer to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss.                       |  sg-056a39927b331918d |  rds-ec2-13                                                                                        |
|  Security group attached to instances to securely connect to cris-developments. Modification could lead to connection loss.                                                                          |  sg-02c5bab98e693460e |  ec2-rds-8                                                                                         |
|  Security group attached to distributedsourcing to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss.                |  sg-017622c701c955d1c |  rds-ec2-10                                                                                        |
|  Security group attached to instances to securely connect to algorand-multisig-test-scalability. Modification could lead to connection loss.                                                         |  sg-0337920ee7d713e29 |  ec2-rds-7                                                                                         |
|  Security group attached to nft-database to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss.                       |  sg-0ae0b624c5a424e86 |  rds-ec2-1                                                                                         |
|  launch-wizard-9 created 2020-11-26T17:39:15.656+01:00                                                                                                                                               |  sg-0119982cd1ae4accc |  launch-wizard-9                                                                                   |
|  launch-wizard-5 created 2022-02-14T10:52:30.489+01:00                                                                                                                                               |  sg-03ba33e28ad1ec4a5 |  Cacti_Server_Security_Group                                                                       |
|  Access Rules for PCS external port                                                                                                                                                                  |  sg-062221c3ee0980adf |  VPNLiquidBackbone-PCSvExternalSecurityGroup-1V10J18KXFIMT                                         |
|  Security group attached to instances to securely connect to postgres-ds-1. Modification could lead to connection loss.                                                                              |  sg-016e425970f2b5014 |  ec2-rds-12                                                                                        |
|  Security group attached to postgres-ds-1 to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss.                      |  sg-08830019a5cee74b4 |  rds-ec2-12                                                                                        |
|  Security group attached to instances to securely connect to distributedsourcing. Modification could lead to connection loss.                                                                        |  sg-08a731b5763c240cb |  ec2-rds-10                                                                                        |
|  Security group attached to instances to securely connect to algo-indexer. Modification could lead to connection loss.                                                                               |  sg-086e99a3ebb8b3d68 |  ec2-rds-13                                                                                        |
|  Backup up of launch-wizard                                                                                                                                                                          |  sg-01270775df06768ac |  0da96193ffc12d846 - launch-wizard-4_backup                                                        |
|  Security group attached to instances to securely connect to nft-database. Modification could lead to connection loss.                                                                               |  sg-0030b7bf8660dd8b5 |  ec2-rds-2                                                                                         |
|  Created by RDS management console                                                                                                                                                                   |  sg-026987ecd3911976e |  nfttape                                                                                           |
|  Access Rules for PCS internal port                                                                                                                                                                  |  sg-0b29fc9ff89e82a17 |  VPNLiquidBackbone-PCSvInternalSecurityGroup-JG5NUTZUHSY3                                          |
|  Security group attached to instances to securely connect to test-tamietti. Modification could lead to connection loss.                                                                              |  sg-0f7559bb4dbefbfe8 |  ec2-rds-9                                                                                         |
|  launch-wizard-7 created 2020-08-07T10:31:27.071+02:00                                                                                                                                               |  sg-0b4cb8677c83cdb53 |  launch-wizard-7                                                                                   |
|  Security group attached to cris-developments to allow EC2 instances with specific security groups attached to connect to the database. Modification could lead to connection loss.                  |  sg-091fdcf4bef361ab8 |  rds-ec2-8                                                                                         |
+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+-----------------------+----------------------------------------------------------------------------------------------------+


--
SG_ID=sg-0a0a1f8f84b186633
SG_NAME=gse_corda_machine
aws ec2 describe-security-groups --group-ids "$SG_ID" \
  --query "SecurityGroups[0].{Ingress:IpPermissions,Egress:IpPermissionsEgress}" \
  --output table