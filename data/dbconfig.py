from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

# Database connection configuration
RDS_PASSWORD = os.environ.get('AWS_RDS_PASSWORD')
db_config = {
    'user': 'admin',
    'password': f"{RDS_PASSWORD}",
    'host': 'multiai2.cb280weeg64t.us-west-2.rds.amazonaws.com',
    'database': 'multiai'
}