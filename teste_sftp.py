import sys
import paramiko

print("Python:", sys.executable)
print("Paramiko:", paramiko.__version__)


try:
    print("Conectando...")

    transport = paramiko.Transport(("10.251.70.27", 22))
    transport.start_client(timeout=10)

    print("Chave do servidor:")
    print(transport.get_remote_server_key())
    print("Tipo da chave:")
    print(transport.get_remote_server_key().get_name())

    transport.close()

except Exception as e:
    import traceback
    print(traceback.format_exc())