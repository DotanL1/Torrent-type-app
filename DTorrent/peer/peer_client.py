import wx
import socket
from curved_button import curved_button
from crypto_utils import recv_by_size,send_with_size,recv_with_AES,send_with_AES
from crypto_utils import recv_by_size, send_with_size,send_with_AES,recv_with_AES
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import pickle
import os
import threading
import time
import hashlib
import random
import requests


APPWIDTH = 1000
APPHEIGHT = 900
server_port = 1235
p2p_port = random.randint(5000,6000)
lock = threading.Lock()

class Torrent_app(wx.Dialog):

    def __init__(self, parent, id, title, ip):
        wx.Dialog.__init__(self, parent, id, title, size=(APPWIDTH, APPHEIGHT))
        self.Show()
        self.deafault_ip = ip
        self.username = ''




        self.p2p_sock = socket.socket()
        self.p2p_sock.bind(('0.0.0.0',p2p_port))
        #try:
           # upnp = miniupnpc.UPnP()
           # upnp.discoverdelay = 200
          #  upnp.discover()
          #  upnp.selectigd()

         #   upnp.addportmapping(p2p_port, 'TCP', upnp.lanaddr, p2p_port, 'DTorrent P2P Port', '')

          #  print(f"[UPnP] Port {p2p_port} forwarded successfully. External IP: {upnp.externalipaddress()}")
       # except Exception as e:
         #   print(f"[UPnP] Port forwarding failed: {e}")
         #   raise
        self.p2p_thread = threading.Thread(target=self.p2p_server,)
        self.p2p_parameters = dh.generate_parameters(generator=2, key_size=512, backend=default_backend())
        self.p2p_DFH_private_key = self.p2p_parameters.generate_private_key()
        self.p2p_DFH_public_key =  self.p2p_DFH_private_key.public_key()
        self.p2p_thread.start()

        self.sock = socket.socket()
        self.listener = threading.Thread(target=self.listen, args=(self.sock,), daemon=True)

        self.my_files = {}
        self.chunks = {}
        self.missing_chunks = []
        self.total_chunks = None
        self.retry_count = 0


        self.server_key = None
        self.login_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.remove_login_error, self.login_timer)

        self.Bind(wx.EVT_CLOSE, self.on_exit)


        self.conn_ip = wx.TextCtrl(self, pos=(320, 200), size=(300, 30))
        self.conn_ip.SetHint('Input tracker server ip:')
        self.conn_btn = curved_button(self,'Connect',size=(160,35),pos=(390,259),radius=13,bg_color=(wx.Colour(255,0,0)))
        self.conn_btn.SetClickCallback(self.connect_tracker)


        self.diss_btn = curved_button(self,'Dissconect',pos=(0,0),size=(100,20),bg_color=(255,0,0))
        self.diss_btn.Hide()
        self.diss_btn.SetClickCallback(self.on_dissconect)





        self.file_lst = wx.ListCtrl(self,style=wx.LC_REPORT | wx.BORDER_SUNKEN,pos=(100,100),size=(800,500))
        self.file_lst.InsertColumn(0, 'Filename', width=300)
        self.file_lst.InsertColumn(1, 'Size', width=100)
        self.file_lst.InsertColumn(2, 'Seeders', width=100)
        self.file_lst.InsertColumn(3, 'Status', width=150)

        self.file_lst.Bind(wx.EVT_LIST_ITEM_ACTIVATED,self.on_file_selected)
        self.file_lst.Hide()
        



















        self.log_btn = curved_button(self, "Login",size=(160, 35),pos=(390,250), radius=13,bg_color=(wx.Colour(222,24,80)))
        self.log_btn.SetClickCallback(self.handle_login )
        self.log_btn.Hide()


        self.or_txt = wx.StaticText(self,pos=(460,297),label='Or')
        self.or_txt.Hide()


        self.signup_btn = curved_button(self,'Signup',size=(160,35),pos = (390,325),radius=15,bg_color=(wx.Colour(136,183,252)))
        self.signup_btn.SetClickCallback(self.handle_signup)
        self.signup_btn.Hide()

        self.name = wx.TextCtrl(self, pos=(320, 130), size=(300, 30))
        self.name.SetHint('Enter your username:')
        self.name.Hide()
        
        self.password = wx.TextCtrl(self, pos=(320, 200), size=(300, 30), style=wx.TE_PASSWORD)
        self.password.SetHint('Enter your password:')
        self.password.Hide()

        self.username_txt = wx.StaticText(self,pos=(320,110),label='Username')
        self.password_txt = wx.StaticText(self,pos=(320,180),label='Password')
        self.username_txt.Hide()
        self.password_txt.Hide()

        self.login_error = wx.StaticText(self,pos=(360,300),label=r'Login\SignUp Unsucessful please try again')
        self.login_error.Hide()


        self.share_file_btn = wx.Button(self,pos=(430,750),label='Share a file',size=(100,50))
        self.share_file_btn.Bind(wx.EVT_BUTTON,self.on_open_file)
        self.share_file_btn.Hide()




    def login_screen(self,show):
        if show:
            self.log_btn.Show()
            self.or_txt.Show()
            self.signup_btn.Show()
            self.name.Show()
            self.password.Show()
            self.username_txt.Show()
            self.password_txt.Show()
            self.conn_btn.Hide()
            self.conn_ip.Hide()
        else:
            self.log_btn.Hide()
            self.or_txt.Hide()
            self.signup_btn.Hide()
            self.name.Hide()
            self.password.Hide()
            self.username_txt.Hide()
            self.password_txt.Hide()
            self.conn_btn.Hide()
            self.conn_ip.Hide()



    def show_connect(self):
        self.log_btn.Hide()
        self.or_txt.Hide()
        self.signup_btn.Hide()
        self.name.Hide()
        self.password.Hide()
        self.username_txt.Hide()
        self.password_txt.Hide()
        self.conn_btn.Show()
        self.conn_ip.Show()
        self.share_file_btn.Hide()
        self.file_lst.Hide()



    def show_list(self, pickled_list):
        self.login_screen(False)
        self.share_file_btn.Show()
        self.file_lst.Show()

        lst = pickle.loads(pickled_list)

        file_map = {}
        for filename, size, seeders in lst:
            if filename not in file_map:
                file_map[filename] = (size, seeders)
            else:
                prev_size, prev_seeders = file_map[filename]
                file_map[filename] = (size, max(prev_seeders, seeders))

        existing_items = {self.file_lst.GetItemText(i, 0): i for i in range(self.file_lst.GetItemCount())}
        seen_files = set()

        for filename, (size, seeders) in file_map.items():
            seen_files.add(filename)
            if filename in existing_items:
                row = existing_items[filename]
                self.file_lst.SetItem(row, 1, str(size))
                self.file_lst.SetItem(row, 2, str(seeders))
            else:
                index = self.file_lst.GetItemCount()
                self.file_lst.InsertItem(index, str(filename))
                self.file_lst.SetItem(index, 1, str(size))
                self.file_lst.SetItem(index, 2, str(seeders))

        for i in reversed(range(self.file_lst.GetItemCount())):
            filename = self.file_lst.GetItemText(i, 0)
            if filename not in seen_files:
                self.file_lst.DeleteItem(i)


            
            
                    













    def handle_login(self):
        send_with_AES(self.sock,f'LOG||{self.name.GetValue() or 'dotan'}||{self.password.GetValue() or '123'}'.encode(),self.server_key)
            

    def handle_signup(self):
        send_with_AES(self.sock, b'SGU||' + self.name.GetValue().encode() + b'||' + self.password.GetValue().encode(), self.server_key)




    def on_dissconect(self):
        try:
            if self.server_key:
                send_with_AES(self.sock, f'EXT||{self.username}'.encode(), self.server_key)
            else:
                send_with_size(self.sock,f'EXT||{self.username}'.encode())
        except:
            pass
        finally:
            self.sock.close()
            self.server_key = None
            self.sock = socket.socket()
            self.file_lst.DeleteAllItems()
            self.name.Clear()
            self.password.Clear()
            self.conn_ip.Clear()
            self.show_connect()
            self.listener = threading.Thread(target=self.listen, args=(self.sock,), daemon=True)





    def on_exit(self, event):
        try:
            if self.server_key:
                send_with_AES(self.sock, f'EXT||{self.username}'.encode(), self.server_key)
            else:
                send_with_size(self.sock,f'EXT||{self.username}'.encode())
        except:
            self.Destroy()
        finally:

            self.Destroy()

        self.Destroy()





    def on_open_file(self, event):
        with wx.FileDialog(self, "Open file",
                          wildcard="All files (*.*)|*.*|Text files (*.txt)|*.txt",
                          style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  
            
            pathname = fileDialog.GetPath()
            self.generate_torrent_file(pathname)


    def on_file_selected(self,event):
        index = event.GetIndex()
        filename = self.file_lst.GetItemText(index)
        query = wx.MessageDialog(self,f'Do you want to download{filename}?','Download confirmatiom',wx.YES_NO | wx.ICON_QUESTION)
        if query.ShowModal() == wx.ID_YES:
            self.start_download(filename)
        query.Destroy()


    def connect_tracker(self):
        try:
            ip = self.conn_ip.GetValue() or self.deafault_ip
            print(f"Connecting to {ip}:{server_port}")
            
            self.sock.connect((ip, server_port))
            self.connected = True
            
            
            self.listener.start()
            
            send_with_size(self.sock, b'DFH||')
            print("Sent DFH request")
            
            timeout_count = 0
            while not self.server_key and timeout_count < 50:  
                time.sleep(0.1)
                timeout_count += 1
                
            if self.server_key:
                print("Key exchange successful!")
                self.login_screen(True)
                self.diss_btn.Show()
            else:
                print("Key exchange timeout")
                
        except Exception as e:
            print(f"Connection error: {e}")
            wx.MessageBox(f"Connection failed: {e}", "Error", wx.OK | wx.ICON_ERROR)
    
    def derive_key(self, shared_secret):
        return hashlib.sha256(shared_secret).digest()[:32]
    

    def sha1_hash(self,data):
        if isinstance(data, str):
            data = data.encode('utf-8')
    
        sha1 = hashlib.sha1()
        sha1.update(data)
        return sha1.hexdigest()

    

    


   
    def p2p_DFH(self,cli_sock, key=None):
        if key:
            try:
                client_public_key_bytes = pickle.loads(key.encode() if isinstance(key, str) else key)
                client_public_key = serialization.load_pem_public_key(
                    client_public_key_bytes, 
                    backend=default_backend()
                )
                
                shared_secret = self.p2p_DFH_private_key.exchange(client_public_key)
                derived_key = derive_key(shared_secret)
                key = derived_key
                
                send_with_size(cli_sock,b'DFH||KEY_ESTABLISHED')
                print(f"Key exchange completed for {cli_sock}")
                return key
                
            except Exception as e:
                print(f"DFH key exchange error: {e}")
                raise
        
        else:
            try:
                data_to_send = {
                    'parameters': self.p2p_parameters.parameter_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.ParameterFormat.PKCS3
                    ),
                    'public_key': self.p2p_DFH_public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                }
                
                serialized_data = pickle.dumps(data_to_send)
                send_with_size(cli_sock,b'DFH||' + serialized_data)
                print(f"Sent DFH parameters to {cli_sock}")
                
            except Exception as e:
                print(f"Error sending DFH parameters:")
                raise



    def handle_DFH(self, data,client=False,p2p_sock=None):
        try:
            if data == 'KEY_ESTABLISHED':
                print("Server confirmed key establishment")
                return
                
            server_data = pickle.loads(data.encode() if isinstance(data, str) else data)
            
            self.dfh_parameters = serialization.load_pem_parameters(
                server_data['parameters'], 
                backend=default_backend()
            )
            
            server_public_key = serialization.load_pem_public_key(
                server_data['public_key'], 
                backend=default_backend()
            )
            
            client_private_key = self.dfh_parameters.generate_private_key()
            client_public_key = client_private_key.public_key()
            
            shared_secret = client_private_key.exchange(server_public_key)
            if client == True:
                key = self.derive_key(shared_secret)
            else:
                self.server_key = self.derive_key(shared_secret)
            
            client_public_key_bytes = client_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            key_data = pickle.dumps(client_public_key_bytes)
            if client:
                send_with_size(p2p_sock, f'DFH||{key_data.decode("latin-1")}'.encode("latin-1"))

            else:
                send_with_size(self.sock, f'DFH||{key_data.decode("latin-1")}'.encode("latin-1"))
            
            print("Sent client public key to server")
            if client:
                return key
            
        except Exception as e:
            print(f"DFH handling error: {e}")
            raise





    def handle_p2p_req(self,file,index,other_sock,key):
        if file in self.my_files.keys():
            path = self.my_files[file]

            piece_length = None
            with open (f'.\\torrent files\\{os.path.splitext(file)[0]}.torrent', 'rb') as f:
                file_data = pickle.loads(f.read())
                piece_length = file_data['piece_length']
            with open (path,'rb') as f:
                f.seek(index * piece_length)
                chunk = f.read(piece_length)
                send_with_AES(other_sock,chunk,key)


        else:
            raise FileNotFoundError
        




    def handle_errors(self,error):
        if error == 'Username taken':
            return False
        elif error == 'DFH_FAILED':
            return True


    
    def show_login_error(self):
        self.login_error.Show()
        self.Layout()
        self.login_timer.Start(3000)
        
    def remove_login_error(self,event):
        self.login_error.Hide()
        self.Layout()


    def listen(self, sock):
        while True:
            
            try:
                sock.settimeout(1)
                if self.server_key:
                        data = recv_with_AES(sock,self.server_key)
                        try:
                            if data == None:
                                return
                            data = data.decode()
                            split_data = data.split('||')
                        except UnicodeDecodeError:
                            split_data = data.split(b'||')
                else:
                    data = recv_by_size(sock)
                    split_data = data.split(b'||')

                
                request_code = split_data[0]


                if request_code == 'LST' or request_code == b'LST':
                    if split_data[1] == 'REFRESH' or split_data[1] == b'REFRESH':
                        send_with_AES(self.sock,'LST||',self.server_key)
                    else:
                        self.show_list(split_data[1])

                elif request_code == 'GET' or request_code == b'GET':
                    self.start_download(data=split_data[1])


                elif request_code == b'DFH':
                    self.handle_DFH(split_data[1])

                elif request_code == 'LOU':
                    wx.CallAfter(self.show_login_error)

                   

                elif request_code == 'LOS':
                    self.username = self.name.GetValue()
                    send_with_AES(sock,b'LST||',self.server_key)

                elif request_code == 'ERR':
                    dissconect = self.handle_errors(split_data[1])
                    if dissconect:
                        sock.close()
                        break



                
            except socket.timeout:
                continue
            except OSError:
                pass

    

    

    





    def generate_torrent_file(self,file_path):
        if os.path.basename(file_path) not in self.my_files.keys():
            chunks,piece_length = self.generate_chunks(file_path)

            piece_length= piece_length * (1024 ** 2)


            torrent_info = {
            "announce": f"{self.conn_ip.GetValue()}:{server_port}",
            "filename": os.path.basename(file_path),
            "size": os.path.getsize(file_path),
            "piece_length": piece_length,
            "pieces": chunks
            }
            os.makedirs('.\\torrent files', exist_ok=True)
            with open (f'.\\torrent files\\{os.path.splitext(os.path.basename(file_path))[0]}.torrent' ,'wb') as f:
                f.write(pickle.dumps(torrent_info))
            
            self.my_files[os.path.basename(file_path)] = file_path

            send_with_AES(self.sock,f'ANN||{os.path.basename(file_path)}||{os.path.getsize(file_path)/(1024**3)}||{piece_length}||{len(chunks)}||{get_local_ip()}||{p2p_port}',self.server_key)
        else:
            print('File already Uploaded')
        
    


    def generate_chunks(self,file_path):
        size = os.path.getsize(file_path)
        gb_size = size / (1024 ** 3)
        chunks = []
        if gb_size < 1:
            pieces = 1
        elif gb_size < 10:
            pieces =4
        elif gb_size <50:
            pieces = 8
        else:
            pieces = 14

        bytes_value = pieces * (1024 ** 2)
        with open (file_path ,'rb') as f:
            amount = 0
            while amount < size:
                chunks.append(self.sha1_hash(f.read(bytes_value)))
                amount += bytes_value

        return chunks,pieces
    


    def start_download(self, file_name=None, data=None):
        if not data:
            send_with_AES(self.sock, f'GET||{file_name}', self.server_key)
        else:
            lst = pickle.loads(data)
            file_name = lst[0].split(',')[0]
            chunk_size = int(lst[0].split(',')[1])
            print(self.missing_chunks)
            if self.missing_chunks:
                print (f'THIS IS SELF  MISSING CHUNKS !!!!!!!!!!!!! {self.missing_chunks}')
                chunks = list.copy(self.missing_chunks)
                missing_chunks = True
            else:
                chunks = int(lst[0].split(',')[2])
                missing_chunks = False
            self.total_chunks = len(chunks) if isinstance(chunks,list) else chunks
            if not missing_chunks:
                self.chunks = {} 

            try:
                from_each_peer = chunks // len(lst)
                remainder = chunks % len(lst)
            except TypeError:
                from_each_peer = len(chunks) // len(lst)
                remainder = len(chunks) % len(lst)

            threads = []
            start_chunk = 0
            print(f'!!!!!!!!THESE ARE THE CHUNKS            {chunks}')
            for conn in range(len(lst)):
                ip = lst[conn].split(',')[3].split(':')[0]
                port = int(lst[conn].split(':')[1])
                chunks_to_download = from_each_peer + (1 if conn < remainder else 0)

                t = threading.Thread(
                    target=self.connect_and_download,
                    args=(ip, port, chunk_size, chunks_to_download, start_chunk, file_name, conn,missing_chunks),
                    daemon=True)
                threads.append(t)
                t.start()

                start_chunk += chunks_to_download

            for t in threads:
                t.join()
            self.missing_chunks = []
            self.build_file(file_name)
 



    def connect_and_download(self, ip, port, chunk_size, chunks_to_download, start_chunk, file_name,tid,missing_chunks):
        download_sock = socket.socket()
        download_sock.connect((ip, port))
        print(self.server_key)
        send_with_size(download_sock, b'DFH||')
        data = recv_by_size(download_sock)
        key = data.split(b'||')[1]
        key = self.handle_DFH(key,True,download_sock)
        data = recv_by_size(download_sock)
        print(data)

        time.sleep(0.5)
        if missing_chunks:
            for i in self.missing_chunks:
                try:
                    send_with_AES(download_sock, f'REQ||{file_name}||{i}'.encode(), key)
                    print(f'Thread number {tid} recived chunk number:  {i}')
                    chunk_data = recv_with_AES(download_sock, key)
                    with lock:
                        self.chunks[i] = chunk_data
                except ConnectionResetError:
                 break
                except OSError:
                 break

        for i in range(start_chunk, start_chunk + chunks_to_download):
            try:
                send_with_AES(download_sock, f'REQ||{file_name}||{i}'.encode(), key)
                print(f'Thread number {tid} recived chunk number:  {i}')
                chunk_data = recv_with_AES(download_sock, key)
            except ConnectionResetError:
                break
            except OSError:
                break

            with lock:
                self.chunks[i] = chunk_data

        download_sock.close()


        
    def build_file(self, name):
        os.makedirs('downloads', exist_ok=True)
        missing = False
        try:
            for i in range(self.total_chunks):
                if i not in self.chunks:
                    self.missing_chunks.append(i)
                    missing = True
                print(f'Got {i}')
        except TypeError:
            for i in range(len(self.total_chunks)):
                if i not in self.chunks:
                    self.missing_chunks.append(i)
                    missing = True
                print(f'Got {i}')



        if missing == True:
            if self.retry_count < 3:
                print(self.missing_chunks)
                self.start_download(name)
                return
            else:
                self.file_lst.SetItem(file_index, 3, 'Download Failed')
                self.retry_count = 0
                return
        

        for i in range(self.file_lst.GetItemCount()):
            if self.file_lst.GetItemText(i, 0) == name:
                file_index = i
                break
        else:
            file_index = -1  

        with open(os.path.join('downloads', name), 'wb') as f:
            for chunk in range(len(self.chunks)):
                f.write(self.chunks[chunk])

                percent = int(((chunk + 1) / self.total_chunks) * 100) if int(((chunk + 1) / self.total_chunks) * 100)< 100 else 100

                if file_index != -1:
                    self.file_lst.SetItem(file_index, 3, f'Downloading... {percent}%')

                wx.Yield()    

        
        self.file_lst.SetItem(file_index, 3, 'Download Complete')
        self.chunks = {}
        self.generate_torrent_file(os.path.join('downloads', name))
        self.retry_count = 0






    def p2p_listener(self,other_sock,addr):
            p2p_key = None
            while True:
                if p2p_key:
                    data = recv_with_AES(other_sock,p2p_key)
                    if data:
                        data = data.decode()
                        spilt_data = data.split('||')
                        request_code = spilt_data[0]
                    else:
                        print('Other Client Dissconected')
                        break
                else:
                    data = recv_by_size(other_sock)
                    spilt_data = data.split(b'||')
                    request_code = spilt_data[0]


                if request_code == 'REQ':
                    self.handle_p2p_req(spilt_data[1],int(spilt_data[2]),other_sock,p2p_key)

                elif request_code == b'DFH':
                    if spilt_data[1]:
                        p2p_key = self.p2p_DFH(other_sock,key=spilt_data[1])
                    else:
                        self.p2p_DFH(other_sock)
                        

                else:
                    print(data)
                    print('ein keshser')
            try:
                other_sock.close()
            except:
                pass
                
                
                    
                  

    def p2p_server(self):
        self.p2p_sock.listen()
        threads = []

        while True:
            other_sock, addr = self.p2p_sock.accept()
            t = threading.Thread(target=self.p2p_listener,args=(other_sock,addr),daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()








        

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))  
    local_ip = s.getsockname()[0]
    s.close()
    return local_ip


def derive_key(shared_secret):
        return hashlib.sha256(shared_secret).digest()[:32]  






if __name__ == "__main__":
    app = wx.App(0)
    Torrent_app(None, -1, 'DTorrent', '127.0.0.1')
    app.MainLoop()