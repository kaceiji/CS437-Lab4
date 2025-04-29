import boto3
import json
import random
import string
import os

# Initialize clients
thingClient = boto3.client('iot')
defaultPolicyName = 'GGTest_Group_Core-policy'  # Update with your policy name
thingGroupName = 'VehicleEmissionsGroup'       # Custom group name

# Directory structure configuration
root_dir = "iot_resources"
certs_dir = os.path.join(root_dir, "certificates")
keys_dir = os.path.join(root_dir, "keys")
data_dir = os.path.join(root_dir, "data")

# Create directories if they don't exist
os.makedirs(certs_dir, exist_ok=True)
os.makedirs(keys_dir, exist_ok=True)
os.makedirs(data_dir, exist_ok=True)

def randomThingName(prefix="vehicle_"):
    """Generate a consistent Thing name with numeric suffix."""
    return f"{prefix}{random.randint(0, 99999):05d}"

def createThingGroup(groupName):
    """Create a Thing Group in AWS IoT if it doesn't exist."""
    try:
        thingClient.create_thing_group(thingGroupName=groupName)
        print(f"✅ Thing Group '{groupName}' created.")
    except thingClient.exceptions.ResourceAlreadyExistsException:
        print(f"⚠️ Thing Group '{groupName}' already exists.")

def createThingWithCertAndAddToGroup(device_id):
    """Create a Thing with consistent naming for MQTT client integration."""
    thingName = f"device_{device_id}"
    print(f"🚀 Creating thing: {thingName}")

    # Create Thing in AWS IoT
    thing = thingClient.create_thing(thingName=thingName)
    thingArn = thing['thingArn']

    # Create keys and certificates for the Thing
    cert = thingClient.create_keys_and_certificate(setAsActive=True)
    certArn = cert['certificateArn']
    certId = cert['certificateId']

    # Save certs with consistent naming pattern
    cert_files = {
        'cert': os.path.join(certs_dir, f"device_{device_id}.pem"),
        'pubkey': os.path.join(keys_dir, f"device_{device_id}.public.pem"),
        'privkey': os.path.join(keys_dir, f"device_{device_id}.private.pem")
    }
    
    with open(cert_files['cert'], 'w') as f:
        f.write(cert['certificatePem'])
    with open(cert_files['pubkey'], 'w') as f:
        f.write(cert['keyPair']['PublicKey'])
    with open(cert_files['privkey'], 'w') as f:
        f.write(cert['keyPair']['PrivateKey'])

    # Attach policy to the certificate
    thingClient.attach_policy(
        policyName=defaultPolicyName,
        target=certArn
    )

    # Attach the certificate to the Thing
    thingClient.attach_thing_principal(
        thingName=thingName,
        principal=certArn
    )

    # Add the Thing to the Thing Group
    thingClient.add_thing_to_thing_group(
        thingGroupName=thingGroupName,
        thingName=thingName
    )

    print(f"✅ {thingName} registered with certificate {certId[:6]}...")
    print(f"   Certificates saved to:\n   - {cert_files['cert']}\n   - {cert_files['privkey']}\n")

    return cert_files

# Create the Thing Group
createThingGroup(thingGroupName)

# Create multiple Things with sequential IDs
num_devices = 10  # Adjust as needed
for device_id in range(num_devices):
    createThingWithCertAndAddToGroup(device_id)

print(f"✅ All {num_devices} devices created and added to group '{thingGroupName}'")
print(f"Certificate files are in: {certs_dir}")
print(f"Key files are in: {keys_dir}")