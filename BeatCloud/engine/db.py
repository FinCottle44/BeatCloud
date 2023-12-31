import logging, decimal, time, json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

class BC_Table:
    def __init__(self, dyn_resource): 
        self.dyn_resource = dyn_resource
        self.table = None

    def exists(self, table_name):
        try: 
            table = self.dyn_resource.Table(table_name)
            table.load()
            exists = True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                exists = False
            else:
                logger.error("Couldn't check table %s exists: %s", table_name, e)
                raise
        else:
            self.table = table  
        return exists

    def create_table(self, table_name):
        attr_defs = [
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'}
        ]
        key_schema = [
            {'AttributeName': 'PK', 'KeyType': 'HASH'},  # Partition key
            {'AttributeName': 'SK', 'KeyType': 'RANGE'},  # Sort key
        ]
        provisioned_throughput = {
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }

        try:
            table = self.dyn_resource.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attr_defs,
                ProvisionedThroughput=provisioned_throughput
            )

            table.wait_until_exists()
        except ClientError as e:
            print(f"Couldn't create table {table_name}. {e}")
            return None
        else:
            self.table = table
        return table
      
    def get_user(self, id):
        try:
            response = self.table.get_item(Key={
                'PK': f'USER#{id}',
                'SK': f'METADATA#{id}'
            })
            return response.get('Item')
        except ClientError as e:
            print(f"Couldn't get user {id}. {e}")
        return None
      
    def get_user_by_stripe_id(self, stripe_id):
        try:
            response = self.table.query(
                IndexName='STRIPE-INDEX',  # Specify the GSI name
                KeyConditionExpression='stripe_id = :stripe_id',  # Define the condition
                ExpressionAttributeValues={':stripe_id': stripe_id},  # Provide the value
            )

            items = response.get('Items', [])
            return items

        except Exception as e:
            print(f"Error querying DynamoDB: {e}")
            return []
    
    def add_user(self, id, name, email, picture, stripe_id, user_usage_reset): # Create user
        try:
            self.table.put_item(
                Item={
                'PK': f'USER#{id}',
                'SK': f'METADATA#{id}',
                'name': name,
                'email': email,
                'picture': picture,
                'stripe_id': stripe_id,
                'asset_count':0,
                'preset_count':0,
                'monthly_video_count':0,
                'video_credits':0,
                'usage_reset_timestamp':user_usage_reset,
                'tier': 'free',
                'has_trialed': False
                }
            )
        except ClientError as e:
            print(f"Couldn't add user {id}. {e}")
        return None
    
    def delete_user(self, user_id):
        try:
            # Get all user items:
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(f"USER#{user_id}")
            )
            for item in response["Items"]:
                self.table.delete_item(
                    Key={
                        'PK': item["PK"],
                        'SK': item["SK"]
                    }
                )
        except ClientError as e:
            print(f"Couldn't delete user {user_id}. {e}")
            return None
    
    def get_user_asset_usage(self, user_id):
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}'
                },
                ProjectionExpression='asset_count'
            )
            return response.get('Item')['asset_count']
        except ClientError as e:
            print(f"Couldn't get asset count for User {user_id}: {e}")
            return e
        
    def increment_user_asset_usage(self, user_id, value):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}' 
                },
                UpdateExpression="SET asset_count = asset_count + :val",
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            print(f"Couldn't get asset count for User {user_id}: {e}")
            return e
        
    def increment_user_credits(self, user_id, value):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}' 
                },
                UpdateExpression="SET video_credits = video_credits + :val",
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            print(f"Couldn't set credits for User {user_id}: {e}")
            return e
        
    def set_user_credits(self, user_id, value):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}' 
                },
                UpdateExpression="SET video_credits = :val",
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            print(f"Couldn't set credits for User {user_id}: {e}")
            return e
        
    def set_user_has_trialed(self, user_id, value):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}' 
                },
                UpdateExpression="SET has_trialed = :val",
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            print(f"Couldn't set credits for User {user_id}: {e}")
            return e
        
    def get_user_preset_usage(self, user_id):
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}'
                },
                ProjectionExpression='preset_count'
            )
            return response.get('Item')['preset_count']
        except ClientError as e:
            print(f"Couldn't get asset count for User {user_id}: {e}")
            return e
        
    def increment_user_preset_usage(self, user_id, value):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}' 
                },
                UpdateExpression="SET preset_count = preset_count + :val",
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
            return response
        except ClientError as e:
            print(f"Couldn't get asset count for User {user_id}: {e}")
            return e

    def get_user_video_usage(self, user_id):
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}'
                },
                ProjectionExpression='monthly_video_count'
            )
            return response.get('Item')['monthly_video_count']
        except ClientError as e:
            print(f"Couldn't get video count for User {user_id}: {e}")
            return e
        
    def increment_user_video_usage(self, user_id, value):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}' 
                },
                UpdateExpression="SET monthly_video_count = monthly_video_count + :val",
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            print(f"Couldn't get asset count for User {user_id}: {e}")
            return e
    
    def set_user_video_usage(self, user_id, value): # Used for resetting to 0
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}' 
                },
                UpdateExpression="SET monthly_video_count = :val",
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            print(f"Couldn't set video usage for User {user_id}: {e}")
            return e
    
    def set_user_usage_reset(self, user_id, value): # Used for resetting to 0
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}' 
                },
                UpdateExpression="SET usage_reset_timestamp = :val",
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            print(f"Couldn't set billing reset for User {user_id}: {e}")
            return e
    
    def set_user_tier(self, user_id, tier): # Used for resetting to 0
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'METADATA#{user_id}' 
                },
                UpdateExpression="SET tier = :val",
                ExpressionAttributeValues={
                    ':val': tier
                },
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            print(f"Couldn't set tier for User {user_id}: {e}")
            return e

    ### Visualizers
    def get_visualizer(self, user_id, visualizer_id):
        try:
            response = self.table.get_item(Key={
                'PK': f'USER#{user_id}',
                'SK': f'VISUALIZER#{visualizer_id}'
            })
            return response.get('Item')
        except ClientError as e:
            print(f"Couldn't get user {id}. {e}")
        return None

    def add_visualizer(self, user_id, visualizer_id, title, created, visualizer_status, yt_id=None):
        try:
            self.table.put_item(
                Item={
                'PK': f'USER#{user_id}',
                'SK': f'VISUALIZER#{visualizer_id}',
                'title': title,
                # 'duration': duration,
                'created': created,
                'visualizer_status': visualizer_status,
                'yt_id': yt_id
                }
            )
        except ClientError as e:
            print(f"Couldn't add visualizer {visualizer_id}. {e}")
        return None
    
    def delete_visualizer(self, user_id, visualizer_id):
        try:
            response = self.table.delete_item(Key={
                'PK': f'USER#{user_id}',
                'SK': f'VISUALIZER#{visualizer_id}'
            })
            return response
        except ClientError as e:
            print(f"Couldn't delete visualizer {visualizer_id}. {e}")
        return None
    
    def get_user_visualizers(self, user_id, sort_by):
        try:
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(f'USER#{user_id}') & Key('SK').begins_with('VISUALIZER#')
            )
            items = response["Items"]
            
            # Sort
            if len(items) > 0:
                if sort_by == 'date_asc':
                    items.sort(key=lambda x: x['created'])
                elif sort_by == "name_asc":
                    items.sort(key=lambda x: x['title'])
                else:  # default to 'date_desc'
                    items.sort(key=lambda x: x['created'], reverse=True)
            
            return response['Items']
        except ClientError as e:
            print(f"Couldn't get visualizers for user {user_id}. {e}")
        return None
        
    def get_visualizer_status_info(self, user_id, visualizer_id):
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'VISUALIZER#{visualizer_id}'
                },
                ProjectionExpression='visualizer_status, ss_task_id, cm_task_id'
            )
            status_info = response.get('Item')
            return True, status_info
        except ClientError as e:
            print(f"Couldn't get status for Visualizer {visualizer_id}: {e}")
            return False, e

    def set_visualizer_status(self, user_id, visualizer_id, visualizer_status):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'VISUALIZER#{visualizer_id}'
                },
                UpdateExpression="set #st=:s",
                ExpressionAttributeNames={
                    '#st': 'visualizer_status'
                },
                ExpressionAttributeValues={
                    ':s': visualizer_status
                },
                ReturnValues="UPDATED_NEW"
            )
            return response
        except ClientError as e:
            print(f"Couldn't update status for visualizer {visualizer_id}. {e}")
            return None

    def set_visualizer_shotstack_id(self, user_id, visualizer_id, shotstack_id):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'VISUALIZER#{visualizer_id}'
                },
                UpdateExpression="set #st=:s",
                ExpressionAttributeNames={
                    '#st': 'ss_task_id'
                },
                ExpressionAttributeValues={
                    ':s': shotstack_id
                },
                ReturnValues="UPDATED_NEW"
            )
            return response
        except ClientError as e:
            print(f"Couldn't update status for visualizer {visualizer_id}. {e}")
            return None

    def set_visualizer_creatomate_id(self, user_id, visualizer_id, creatomate_id):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'VISUALIZER#{visualizer_id}'
                },
                UpdateExpression="set #st=:s",
                ExpressionAttributeNames={
                    '#st': 'cm_task_id'
                },
                ExpressionAttributeValues={
                    ':s': creatomate_id
                },
                ReturnValues="UPDATED_NEW"
            )
            return response
        except ClientError as e:
            print(f"Couldn't update status for visualizer {visualizer_id}. {e}")
            return None
  
  ### Presets:
    def get_preset(self, user_id, preset_id):
        try:
            response = self.table.get_item(Key={'PK': f'USER#{user_id}', 'SK': f'PRESET#{preset_id}'})
            return response.get("Item")
        except ClientError as e:
            print(f"Couldn't get preset {preset_id}. {e}")
            return None

    def add_preset(self, user_id, preset_id, preset_name, preset_data):
        try:
            response = self.table.put_item(
                Item={
                    'PK': f'USER#{user_id}',
                    'SK': f'PRESET#{preset_id}',
                    'preset_name': preset_name,
                    'preset_data': preset_data
                }
            )
            return response
        except ClientError as e:
            print(f"Couldn't add preset {preset_id}. {e}")
            return None
    
    def get_all_presets(self, user_id):
        try:
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(f'USER#{user_id}') & Key('SK').begins_with('PRESET#')
            )
            return response.get("Items")
        except ClientError as e:
            print(f"Couldn't get presets for user {user_id}. {e}")
            return None

    def update_preset(self, user_id, preset_id, preset_name, preset_data):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'PRESET#{preset_id}'
                },
                UpdateExpression="set preset_name=:n, preset_data=:d",
                ExpressionAttributeValues={
                    ':n': preset_name,
                    ':d': preset_data
                },
                ReturnValues="UPDATED_NEW"
            )
            return response
        except ClientError as e:
            print(f"Couldn't update preset {preset_id}. {e}")
            return None

    def delete_preset(self, user_id, preset_id):
        try:
            response = self.table.delete_item(Key={'PK': f'USER#{user_id}', 'SK': f'PRESET#{preset_id}'})
            return response
        except ClientError as e:
            print(f"Couldn't delete preset {preset_id}. {e}")
            return None
        
  ### YouTube Upload Templates:
    def get_template(self, user_id, template_id):
        try:
            response = self.table.get_item(Key={'PK': f'USER#{user_id}', 'SK': f'TEMPLATE#{template_id}'})
            return response.get("Item")
        except ClientError as e:
            print(f"Couldn't get template {template_id}. {e}")
            return None

    def add_template(self, user_id, template_id, template_name, template_data):
        try:
            response = self.table.put_item(
                Item={
                    'PK': f'USER#{user_id}',
                    'SK': f'TEMPLATE#{template_id}',
                    'template_name': template_name,
                    'template_data': template_data
                }
            )
            return response
        except ClientError as e:
            print(f"Couldn't add template {template_id}. {e}")
            return None
    
    def get_all_templates(self, user_id):
        try:
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(f'USER#{user_id}') & Key('SK').begins_with('TEMPLATE#')
            )
            return response.get("Items")
        except ClientError as e:
            print(f"Couldn't get templates for user {user_id}. {e}")
            return None

    def update_template(self, user_id, template_id, template_name, template_data):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'TEMPLATE#{template_id}'
                },
                UpdateExpression="set template_name=:n, template_data=:d",
                ExpressionAttributeValues={
                    ':n': template_name,
                    ':d': template_data
                },
                ReturnValues="UPDATED_NEW"
            )
            return response
        except ClientError as e:
            print(f"Couldn't update template {template_id}. {e}")
            return None

    def delete_template(self, user_id, template_id):
        try:
            response = self.table.delete_item(Key={'PK': f'USER#{user_id}', 'SK': f'TEMPLATE#{template_id}'})
            return response
        except ClientError as e:
            print(f"Couldn't delete template {template_id}. {e}")
            return None

### YT:
    def set_visualizer_yt_id(self, user_id, visualizer_id, yt_id):
        try:
            response = self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'VISUALIZER#{visualizer_id}'
                },
                UpdateExpression="set #yt=:id",
                ExpressionAttributeNames={
                    '#yt': 'yt_id'
                },
                ExpressionAttributeValues={
                    ':id': yt_id
                },
                ReturnValues="UPDATED_NEW"
            )
            return response
        except ClientError as e:
            print(f"Couldn't update ID for visualizer {visualizer_id}. {e}")
            return None

    # Convert floats to decimal
    def convert_floats(self, obj):
        if isinstance(obj, list):
            return [self.convert_floats(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self.convert_floats(v) for k, v in obj.items()}
        elif isinstance(obj, float):
            return decimal.Decimal(str(obj))
        else:
            return obj
    
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)