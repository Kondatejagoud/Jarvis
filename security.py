import io
import os
import keyring
import torch
from cryptography.fernet import Fernet
import config

def get_or_create_key() -> bytes:
    """
    Retrieve the AES encryption key from the OS credential store (Windows Credential Manager).
    If it doesn't exist, generate a new one, store it, and return it.
    """
    stored_key = keyring.get_password(config.KEYRING_SERVICE, config.KEYRING_ACCOUNT)
    
    if stored_key is None:
        # Generate a new Fernet key (32 url-safe base64-encoded bytes)
        new_key = Fernet.generate_key()
        # Keyring expects a string password
        keyring.set_password(config.KEYRING_SERVICE, config.KEYRING_ACCOUNT, new_key.decode('utf-8'))
        return new_key
    
    return stored_key.encode('utf-8')

def encrypt_embedding(embedding: torch.Tensor, output_path: str) -> None:
    """
    Serialize the speaker embedding tensor, encrypt it using Fernet (AES-128 in CBC mode with SHA256 HMAC),
    and save it to the specified output file path.
    """
    key = get_or_create_key()
    fernet = Fernet(key)
    
    # Serialize PyTorch tensor to bytes
    buffer = io.BytesIO()
    torch.save(embedding, buffer)
    serialized_data = buffer.getvalue()
    
    # Encrypt the serialized data
    encrypted_data = fernet.encrypt(serialized_data)
    
    # Write to file
    with open(output_path, 'wb') as f:
        f.write(encrypted_data)

def decrypt_embedding(input_path: str) -> torch.Tensor:
    """
    Read the encrypted embedding from disk, decrypt it using the key from the OS credential store,
    and deserialize it back into a PyTorch tensor.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Encrypted embedding file not found at: {input_path}")
        
    key = get_or_create_key()
    fernet = Fernet(key)
    
    # Read encrypted data
    with open(input_path, 'rb') as f:
        encrypted_data = f.read()
        
    # Decrypt data
    decrypted_data = fernet.decrypt(encrypted_data)
    
    # Deserialize back to PyTorch tensor
    buffer = io.BytesIO(decrypted_data)
    # Using weights_only=True is a security best practice for loading PyTorch objects
    return torch.load(buffer, weights_only=True)

def get_or_create_audit_key() -> bytes:
    """
    Retrieve the Audit Log encryption key from Windows Credential Manager.
    If it doesn't exist, generate a new one, store it, and return it.
    """
    stored_key = keyring.get_password(config.KEYRING_SERVICE, config.AUDIT_LOG_KEYRING_ACCOUNT)
    
    if stored_key is None:
        new_key = Fernet.generate_key()
        keyring.set_password(config.KEYRING_SERVICE, config.AUDIT_LOG_KEYRING_ACCOUNT, new_key.decode('utf-8'))
        return new_key
        
    return stored_key.encode('utf-8')

def encrypt_log_data(data: str) -> bytes:
    """
    Encrypt a plaintext log string using Fernet.
    """
    key = get_or_create_audit_key()
    fernet = Fernet(key)
    return fernet.encrypt(data.encode('utf-8'))

def decrypt_log_data(encrypted_data: bytes) -> str:
    """
    Decrypt an encrypted log payload using Fernet.
    """
    key = get_or_create_audit_key()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data).decode('utf-8')


