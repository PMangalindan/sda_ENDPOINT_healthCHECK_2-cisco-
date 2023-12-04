#!/usr/bin/env python
# coding: utf-8

# In[1]:


from netmiko import ConnectHandler
import textfsm
import textwrap
from tabulate import tabulate


# In[2]:


def import_instance_id_and_macs():
    ''' import instance-ids and their macs from sda_endpoint_macs.txt file'''
    with open("sda_endpoint_macs.txt") as settings_file:
        sda_endpoint_macs = settings_file.readlines()

    instance_id_macs_dict = {}

    for line in sda_endpoint_macs:
        if 'instance-id'.lower() in line:

            key = line.split("instance-id")[1].split('\n')[0].strip()

            instance_id_macs_dict[key] = []

            latest_key = key
        else:

            if len(line.strip()) > 0:
                instance_id_macs_dict[latest_key].append(line.strip())
                
    return  instance_id_macs_dict  


# In[ ]:





# In[ ]:





# In[4]:


def get_value(key):
    
    
    ''' gets variable values from settings file.
        MAKE SURE TO PUT THE RIGHT SETTINGS FILE PATH '''
    
    key = key
    with open("settings.txt") as settings_file:
            settings_file = settings_file.read()

    if '#' in settings_file.split(key)[0].split("\n")[-1]:
        msg = 'value is commented out'
        print(msg)
        return None
    
     
    else:
        #var = settings_file.split(key)[1].split("\n")[0].strip(" ").strip("\"").strip("\'")

        #print(key)

        unstriped = settings_file.split(key)[1].split("\n")[0].strip()

        #print(unstriped)
        if '"' == unstriped[0]  or '"' == unstriped[-1] or "'" == unstriped[0]  or "'" == unstriped[-1]:
            #print("is string")
            var = unstriped.strip("\"").strip("\'")
            return var
        elif  unstriped.isnumeric():
            var = int(unstriped)
            return var
        elif unstriped.lower() == 'true':
            var = True
            return var
        elif unstriped.lower() ==  'false':
            var = False
            return var
        
        elif unstriped.lower()[0] ==  '[' and unstriped.lower()[-1] == ']':
            var = unstriped
            return var
        
        else:
            print(f"{unstriped} -invalid variable set in settings")


# In[5]:


def ssh_to_device(device_name):
    
    '''creates ConnectHandler instance'''
    
    device_type= get_value(f'{device_name}_device_type=')
    ip= get_value(f'{device_name}_ip=')
    username= get_value(f'{device_name}_username=')
    password= get_value(f'{device_name}_password=')
    secret=  get_value(f'{device_name}_secret=')
    
    
    
    try:
        net_connect = ConnectHandler(  # Uses Netmiko Connect Handler to Connect to the device through SSH
                        device_type=device_type,
                        ip=ip,
                        username=username,
                        password=password,
                        secret=secret,
                        global_delay_factor=1,
                        verbose = True,
                        blocking_timeout = 60,
                        fast_cli = False,
                        auth_timeout = 60,
                        
                    )
    except:
        print(f'Failed to Connect to {device_name}')
    return net_connect


# In[6]:


def send_command_and_textfsm_the_response(cmd, net_connect, textfsm_file_path):
    
    '''returns list of extracted data'''
    
    net_connect = net_connect
    cmd = cmd
    textfsm_file_path = textfsm_file_path
    
    output = net_connect.send_command(cmd, expect_string=r"#", read_timeout=30)
    
    
    
    
    with open(textfsm_file_path) as template: 
        re_table = textfsm.TextFSM(template)
        #print(re_table)
    extracted_data = re_table.ParseText(output)
    


    return extracted_data, output


# # phase 1 importing macs

# In[7]:


end_macs = import_instance_id_and_macs()
print(end_macs)


# # phase 2 get the ip of the macs

# In[70]:


fe1_net_conn = ssh_to_device('BGTA-46-1-106-FLR-6E')


# In[115]:


main_input_data = {}
no_ip_found = []
for k, v in end_macs.items():
    
    #print(k)
    vrf_name = k.split(':')[1]
    
    
    cmd = f'show arp vrf {vrf_name}'
    textfsm_file_path = "textfsm_files\cisco_ios_show_arp_vrf.textfsm"
    ip_mac_map, output = send_command_and_textfsm_the_response(cmd, fe1_net_conn, textfsm_file_path)
    
    main_input_data[k] = []
    for e in ip_mac_map:
        #print(e)
        
        
        for mac in end_macs[k]:
            
            if e[1] == mac:


                main_input_data[k].append(e)
                
                break
                
            else:
                temp_bucket = []
                temp_bucket.append(mac)
                temp_bucket.append('none')
                temp_bucket.append(k.split(':')[1])
                temp_bucket.append(k.split(':')[0])

                temp_bucket.append('BGTA-46-1-106-FLR-6E') #iid
                temp_bucket.append('BGTA-MAN1-46-254') #iid

                temp_bucket.append('nan')
                temp_bucket.append('nan')
                temp_bucket.append('nan')

                no_ip_found.append(temp_bucket) 

            


# In[ ]:





# In[116]:


no_ip_found_clean = []
for el in no_ip_found:
    
    
    if el not in no_ip_found_clean:
        no_ip_found_clean.append(el)


# In[123]:


tabul_no_hits = tabulate(no_ip_found_clean, headers=["MAC", "IP", "VRF", 'INSTANCE ID', "LOCAL FE SWITCH", "CP SWITCH", "REGISTERED", "FE IP", "IP"], tablefmt="orgtbl", maxcolwidths=[None, None])


# In[124]:


print(tabul_no_hits)


# # phase 3 check the control plane switch if the end devices are registered

# In[130]:


cp_net_conn = ssh_to_device('BGTA-MAN1-46-254')


# In[137]:


master_list = []
for k, v in main_input_data.items():
    
    #print(k)
    instance_id = k.split(':')[0]
    
    
        
    cmd = f'show lisp site instance-id {instance_id}'
    textfsm_file_path = "textfsm_files\cisco_ios_show_device-tracking_database.textfsm"
    
    
    extracted_data , output = send_command_and_textfsm_the_response(cmd, cp_net_conn, textfsm_file_path)
    
    extracted_texted = "\n".join([dat[-1] for dat in extracted_data])
    
    
    
    
    
    

    for ipmac in main_input_data[k]:
        temp_bucket_list = []
        ip = ipmac[0]        
        ip = f'{ip}/32'
        #print(ip)
        
        
        temp_bucket_list.append(ipmac[1])
        temp_bucket_list.append(ipmac[0])
        temp_bucket_list.append(k.split(':')[1]) #vrf
        temp_bucket_list.append(k.split(':')[0]) #iid
        
        temp_bucket_list.append('BGTA-46-1-106-FLR-6E') #iid
        temp_bucket_list.append('BGTA-MAN1-46-254') #iid
        no_match = 1
        for register in extracted_data:
            
            if ip in register[2]:

                #print(f'{k} - {ip} is registered --')
                temp_bucket_list.append(register[0])
                temp_bucket_list.append(register[1])
                temp_bucket_list.append(register[2])
                
                no_match = 0
                break

        if no_match == 1:
            #print(f'{k} - {ip} not registered')
            temp_bucket_list.append('no')
            temp_bucket_list.append('nan')
            temp_bucket_list.append('nan')
            
        master_list.append(temp_bucket_list)


# In[142]:


for el in no_ip_found_clean:
    master_list.append(el)


# In[ ]:





# In[143]:


main_tabul = tabulate(master_list, headers=["MAC", "IP", "VRF", 'INSTANCE ID', "LOCAL FE SWITCH", "CP SWITCH", "REGISTERED", "FE IP", "IP"], tablefmt="orgtbl", maxcolwidths=[None, None])


# In[144]:


print(main_tabul)


with open(f'report_xx-xx-xx.txt', 'w') as f:
    f.write(main_tabul)




