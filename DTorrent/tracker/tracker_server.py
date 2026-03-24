import threading
import socket
import hashlib
import secrets
from AsyncMessages import AsyncMessages
from crypto_utils import recv_by_size, send_with_size,send_with_AES,recv_with_AES
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import pickle
import os
import  time


lock = threading.Lock()
key_by_socket = {}
am = AsyncMessages()


parameters = dh.generate_parameters(generator=2, key_size=512, backend=default_backend())

DFH_private_key = parameters.generate_private_key()
DFH_public_key = DFH_private_key.public_key()

user_list = {}
connected_users = []
file_peers = {}
#peer_entry = (username,file_name,file_size,ip,port)





def handle_client(cli_sock,addr):
    while True:
            try:
                cli_sock.settimeout(1)
                if cli_sock not in key_by_socket.keys():
                    data = recv_by_size(cli_sock)
                    split_data = data.split(b'||')
                    
                else:
                    data = recv_with_AES(cli_sock,key_by_socket[cli_sock]).decode()
                    split_data = data.split('||')
                
                
                request_code = split_data[0]
                if request_code == 'LST':
                    show_list(cli_sock,file_peers)

                elif request_code == 'ANN':
                    handle_announce(cli_sock,split_data[1],split_data[2],split_data[3],split_data[4],split_data[5],split_data[6])
                    #cli_sock,file_name,file_name,file_size,ip,port

                elif request_code == 'GET':
                    handle_get(cli_sock,split_data[1])

                

                elif request_code == 'LOG':
                    handle_login(split_data[1],split_data[2],cli_sock)

                elif request_code == 'SGU':
                    handle_signup(split_data[1], split_data[2], cli_sock)
                
                elif request_code == 'EXT':
                    handle_exit(cli_sock)


                elif request_code == b'DFH':
                    if split_data[1]:
                        handle_DFH(cli_sock,key=split_data[1])
                    else:
                        handle_DFH(cli_sock)
                    time.sleep(0.1)
                
            

            except socket.timeout:
                with lock:
                    msgs = am.get_async_messages_to_send(cli_sock)
                    if msgs:
                        for msg in msgs:
                                if cli_sock in key_by_socket:
                                    send_with_AES(cli_sock, msg, key_by_socket[cli_sock])
                                else:
                                    send_with_size(cli_sock, msg)
            except ConnectionResetError as e:
                handle_exit(cli_sock)
                break
            except OSError as e:
                handle_exit(cli_sock)
                break
            



def handle_announce(cli_sock,file_name,file_size,chunk_size,chunks,ip,port):
    with lock:
        username = am.sock_by_user[cli_sock]
        print(am.sock_by_user.keys())
        if file_name not in file_peers:
            file_peers[file_name] = []
        if float(file_size) >= 1:
            file_size = str(round(float(file_size))) + ' GB'
        else:
            mb_size = float(file_size) * 1024
            if mb_size >= 1:
                file_size = str(round(mb_size)) + ' MB'
            else:
                kb_size = mb_size * 1024
                if kb_size >= 1:
                    file_size = str(round(kb_size)) + ' KB'
                else:
                    file_size = '0 KB'
        peer_entry = (username,file_name,file_size,chunk_size,chunks,ip,port)
        if peer_entry not in file_peers[file_name]:
            file_peers[file_name].append(peer_entry)

        show_list(cli_sock,file_peers)
        am.put_msg_to_all(b'LST||REFRESH')
        

def handle_get(cli_sock,file_name):
    peers = [] 
    if file_name in file_peers:
        for p in file_peers[file_name]:
            file_name = p[1]
            chunks = p[4]
            chunk_size = p[3]
            ip = p[5]
            port = p[6]
            peers.append(f'{file_name},{chunk_size},{chunks},{ip}:{port}')
        am.put_msg_in_async_msgs(b'GET||' +pickle.dumps(peers),cli_sock)



def show_list(cli_sock, file_peers):
    lst = []
    for file_name, entries in file_peers.items():
        for entry in entries:
            filename = entry[1]  
            size = entry[2]    
            seeders = len(file_peers[file_name])  
            lst.append((filename, size, seeders))
    am.put_msg_in_async_msgs(b'LST||' + pickle.dumps(lst), cli_sock)

#file_peers = {'eurfhqweoiufygq0e9duwefpq9uwehfqw9eufh' : [('babale','Elden Ring.exe','5GB','192.168.10.12','5000')]}













def hashdata(data):
    return hashlib.sha256(data.encode()).hexdigest()

def salt_password(password):
    salt = secrets.token_hex(16)
    hashed_pass = hashdata(password + salt)
    return f'{hashed_pass}:{salt}'

def load_users():
    global user_list
    user_list.clear()
    if os.path.exists('Users.pkl'):
        with open('Users.pkl', 'rb') as f:
            try:
                while True:
                    user = pickle.load(f)
                    split_user_data = user.split(':')
                    username = split_user_data[0]
                    hashed_password = split_user_data[1]
                    salt = split_user_data[2]
                    user_list[username] = (hashed_password, salt)
            except EOFError:
                pass
            except:
                raise


def handle_login(username, password, cli_sock):
    if username in user_list:
        stored_hashed_pass, salt = user_list[username]
        login_attempt_hash = hashdata(password+salt)
        if login_attempt_hash == stored_hashed_pass:
            with lock:
                if username not in connected_users: 
                    am.sock_by_user[cli_sock] = username
                    am.put_msg_in_async_msgs(f'LOS||{username}||Login Successful'.encode(), cli_sock)

                    serielized_users = pickle.dumps(connected_users)
                    am.put_msg_in_async_msgs(b'USR||' + serielized_users, cli_sock)
                    am.put_msg_to_all(f'NEW||User {username} connected')
                    connected_users.append(username)
                    return
    am.put_msg_in_async_msgs(b'LOU||', cli_sock)



def handle_signup(username, password, cli_sock):
    with lock:
        if username in user_list:
            am.put_msg_in_async_msgs(b'ERR||Username taken', cli_sock)
        else:
            with open('Users.pkl', 'ab') as f:
                pickle.dump(f'{username}:{salt_password(password)}', f)
            load_users()
            am.put_msg_in_async_msgs(b'SUS||Sign Up Successful', cli_sock)








def handle_exit(cli_sock):
    with lock:
        username = am.sock_by_user.get(cli_sock)
        if username:
            if username in connected_users:
                connected_users.remove(username)

            for file_name in list(file_peers.keys()):
                original_entries = file_peers[file_name]
                file_peers[file_name] = [
                    entry for entry in original_entries if entry[0] != username
                ]
                if not file_peers[file_name]:
                    file_peers.pop(file_name, None)


            am.sock_by_user.pop(cli_sock, None)
    cli_sock.close()




def derive_key(shared_secret):
    return hashlib.sha256(shared_secret).digest()[:32]  


def handle_DFH(cli_sock, key=None):
    if key:
        try:
            client_public_key_bytes = pickle.loads(key.encode() if isinstance(key, str) else key)
            client_public_key = serialization.load_pem_public_key(
                client_public_key_bytes, 
                backend=default_backend()
            )
            
            shared_secret = DFH_private_key.exchange(client_public_key)
            derived_key = derive_key(shared_secret)
            key_by_socket[cli_sock] = derived_key
            
            am.put_msg_in_async_msgs(b'DFH||KEY_ESTABLISHED',cli_sock)
            print(f"Key exchange completed for {cli_sock}")
            
        except Exception as e:
            print(f"DFH key exchange error: {e}")
            am.put_msg_in_async_msgs( b'ERR||DFH_FAILED',cli_sock)
    
    else:
        try:
            data_to_send = {
                'parameters': parameters.parameter_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.ParameterFormat.PKCS3
                ),
                'public_key': DFH_public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            }
            
            serialized_data = pickle.dumps(data_to_send)
            am.put_msg_in_async_msgs( b'DFH||' + serialized_data,cli_sock)
            print(f"Sent DFH parameters to {cli_sock}")
            
        except Exception as e:
            print(f"Error sending DFH parameters:")
            raise
















def main():
    srv_sock = socket.socket()
    srv_sock.bind(('0.0.0.0',1235))
    srv_sock.listen(500)
    print('Listening')
    while True:
        cli_sock, adress = srv_sock.accept()
        print(f'Connection from {adress}')
        am.add_new_socket(cli_sock)
        t = threading.Thread(target=handle_client,args=(cli_sock,adress),daemon=True)
        t.start()





if __name__ == '__main__':
    load_users()
    main()