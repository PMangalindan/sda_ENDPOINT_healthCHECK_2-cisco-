
from netmiko import ConnectHandler
import textfsm
import textwrap
from tabulate import tabulate
import re
from datetime import datetime
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
# In[60]:
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
        #print(unstriped[0])
        if unstriped.lower()[0] ==  '[' and unstriped.lower()[-1] == ']':
            var1 = unstriped.strip('[').strip(']').split(',')
            var = [e.strip().strip("'").strip('"') for e in var1]
            return var
        elif '"' == unstriped[0]  or '"' == unstriped[-1] or "'" == unstriped[0]  or "'" == unstriped[-1]:
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
        else:
            print(f"{unstriped} -invalid variable set in settings")
# In[4]:
def ssh_to_device(device_name):
    '''creates ConnectHandler instance'''
    device_type= get_value(f'device_type=')
    ip= get_value(f'{device_name}_ip=')
    username= get_value(f'username=')
    password= get_value(f'password=')
    secret=  get_value(f'secret=')
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
# In[5]:
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
# In[6]:
def mac_verify(mac):
    ''' verifies mac format '''
    mac = mac
    regex = "^([0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}$"
    if re.match(regex, mac):
        return True
    else:
        return False
# In[7]:
def sort_by_line_num(elem):
    """use as (key) parameter in list.sort(key=) """
    line = elem[5] # edit for situation
    #print(line)
    return line
# In[ ]:
# In[8]:
def phase_2(end_macs,fe_infos,cp_infos ):
    end_macs = end_macs
    fe1_net_conn = ssh_to_device(fe_infos['name'])
    main_input_data = {}
    no_ip_found = []
    for k, v in end_macs.items():
        #print(k)
        vrf_name = k.split(':')[1]
        cmd = f'show arp vrf {vrf_name}'
        textfsm_file_path = "textfsm_files\cisco_ios_show_arp_vrf.textfsm"
        ip_mac_map, output = send_command_and_textfsm_the_response(cmd, fe1_net_conn, textfsm_file_path)
        main_input_data[k] = []
        #print(vrf_name)
        for e in ip_mac_map:
            #print('#######################')
            #print(e)
            for mac in end_macs[k]:
                #print('________________________')
                #print( end_macs[k])
                if e[1] == mac:
                    main_input_data[k].append(e)
                    break
                else:
                    #print(len(end_macs[k]) - 1)
                    #print(end_macs[k].index(mac))
                    temp_bucket = []
                    temp_bucket.append(mac)
                    temp_bucket.append('not found')
                    temp_bucket.append(k.split(':')[1])
                    temp_bucket.append(k.split(':')[0])
                    temp_bucket.append(fe_infos['name']) #iid
                    #temp_bucket.append('BGTA-MAN1-46-254') #iid
                    temp_bucket.append('--')
                    #if end_macs[k].index(mac) == len(end_macs[k]) - 1:
                    no_ip_found.append(temp_bucket) 
    no_ip_found_clean = []
    no_ip_found_clean2 = []
    for matched in main_input_data.values():
        for el in no_ip_found:
            for macip in matched:
                #print(macip)
                #print(el[0])
                if el[0] in macip:
                    del no_ip_found[no_ip_found.index(el)]
    for el in no_ip_found:
        if el not in no_ip_found_clean:
            if mac_verify(el[0]):
                el.append("mac's ip not found in this FE's arp table")
                no_ip_found_clean.append(el)
            else:
                el.append('invalid mac format')
                no_ip_found_clean.append(el)
    for el in no_ip_found_clean:
        if el not in no_ip_found_clean2:
            no_ip_found_clean2.append(el)
    #print(no_ip_found_clean2)
    tabul_no_hits = tabulate(no_ip_found_clean2, headers=["MAC", "IP", "VRF", 'INSTANCE ID', "LOCAL FE SWITCH", "REGISTERED", 'MESSAGE'], tablefmt="orgtbl", maxcolwidths=[None, None])  
    return no_ip_found_clean2, main_input_data
# In[9]:
def phase_3(main_input_data, no_ip_found_clean2, fe_infos,cp_infos):
    cp_net_conn = ssh_to_device(cp_infos['name'])
    master_list = []
    for k, v in main_input_data.items():
        #print(k)
        instance_id = k.split(':')[0]
        cmd = f'show lisp site instance-id {instance_id}'
        textfsm_file_path = "textfsm_files\cisco_ios_show_device-tracking_database.textfsm"
        extracted_data , output = send_command_and_textfsm_the_response(cmd, cp_net_conn, textfsm_file_path)
        extracted_texted = "\n".join([dat[-1] for dat in extracted_data])
        #print('__________________')
        #print(main_input_data)
        #print('__________________')
        for ipmac in main_input_data[k]:
            temp_bucket_list = []
            ip = ipmac[0]        
            ip = f'{ip}/32'
            #print(ip)
            temp_bucket_list.append(ipmac[1])
            temp_bucket_list.append(ipmac[0])
            temp_bucket_list.append(k.split(':')[1]) #vrf
            temp_bucket_list.append(k.split(':')[0]) #iid
            temp_bucket_list.append(fe_infos['name']) #iid
            #temp_bucket_list.append('BGTA-MAN1-46-254') #iid
            no_match = 1
            for register in extracted_data:
                #print(ip)
                #print(register)
                if ip in register[2]:
                    #print(register)
                    #print(f'{k} - {ip} is registered --')
                    if "yes#" == register[0]:
                        yup = 'REGISTERED'
                        temp_bucket_list.append(yup)
                        temp_bucket_list.append('-----')
                    no_match = 0
                    break
            if no_match == 1:
                #print(f'{k} - {ip} not registered')
                temp_bucket_list.append('--')
                temp_bucket_list.append('INVESTIGATE')
            master_list.append(temp_bucket_list)
    for el in no_ip_found_clean2:
        master_list.append(el)
    return master_list
# In[10]:
'''main_tabul = tabulate(master_list, headers=["MAC", "IP", "VRF", 'INSTANCE ID', "LOCAL FE SWITCH", "REGISTRY STAT", 'MESSAGE'], tablefmt="orgtbl")
date_now = datetime.now().strftime("%m-%d-%y_%H%M")
cp_switch_name = cp_infos['name']
print(f'{cp_switch_name} (CP)')
print(date_now)
print(main_tabul)'''
# In[11]:
def phase_4(master_list, fe_infos,cp_infos):
    for entry in master_list:
        if entry[-1] == 'INVESTIGATE':
            #print(entry[-1])
            #fe1_net_conn = ssh_to_device(fe_infos[loopback']['name'])
            ################################################################################ CHECK 1 
            cp_net_conn = ssh_to_device(cp_infos['name'])
            vrf = entry[2]
            cmd = f'show lisp site rloc members eid-table {vrf}'
            output = cp_net_conn.send_command(cmd, expect_string=r"#", read_timeout=30)
            #print(output)
            cp_net_conn.disconnect()
            if fe_infos['loopback0'] in output:
                #print('the end device could have disconnected re-checking the  FE arp table')
                ########################################################################################## CHECK 2
                fe1_net_conn = ssh_to_device(fe_infos['name'])
                cmd = f'show arp vrf {entry[2]}'
                textfsm_file_path = "textfsm_files\cisco_ios_show_arp_vrf.textfsm"
                ip_mac_map, output = send_command_and_textfsm_the_response(cmd, fe1_net_conn, textfsm_file_path)
                #print(output)
                if entry[1] in output:
                    """print('''this end device is not registered. it is possible that 
                        this device have not yet connected outside its FE's direct connections.''')"""
                    ent_index = master_list.index(entry)
                    del master_list[ent_index][-1]
                    loopback_ip =fe_infos['loopback0']
                    master_list[ent_index].append(f"this end device is not registered. this device could be turned off.")
                    pattern = r"-+\s+([0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4})\b"
                    # Search for MAC address using regex
                    mac_address = re.findall(pattern, output)
                    for mac in mac_address:
                        if mac == entry[0]:
                            ent_index = master_list.index(entry)
                            del master_list[ent_index][-1]
                            loopback_ip =fe_infos['loopback0']
                            master_list[ent_index].append(f"this end device is an incomplete aging status. one reason is that this device could be powered off.")
            else:
                ent_index = master_list.index(entry)
                #print(ent_index)
                del master_list[ent_index][-1]
                loopback_ip =fe_infos['loopback0']
                master_list[ent_index].append(f'FE loopback0 ({loopback_ip})is not in the lisp site rloc members eid-table {vrf}')
    master_list.sort(key=sort_by_line_num, reverse=True) ### sort lines
    return master_list
# In[22]:
def final_phase(master_list,cp_infos, fe_infos, cp_i,fe_i):
    fe_i = fe_i
    merge_ = []
    clean_master_list = []
    for dat in master_list:
        #print(dat)
        del dat[4]
        clean_master_list.append(dat) # redundant really
    main_tabul = tabulate(clean_master_list, headers=["MAC", "IP", "VRF", 'INSTANCE ID', "REGISTRY STAT", 'MESSAGE'], tablefmt="orgtbl",maxcolwidths=[None, None, None, None, None, 40])
    date_now = datetime.now().strftime("%m-%d-%y_%H-%M-%S") 
    cp_switch_name = cp_infos['name']
    fe_switch_name = fe_infos['name']
    print(f'{cp_switch_name} (CP_{cp_i})')
    print(f'{fe_switch_name} (FE_{fe_i})')
    print(date_now)
    print(main_tabul)
    merge_.append(f'{cp_switch_name} (CP_{cp_i})')
    merge_.append(f'{fe_switch_name} (FE_{fe_i})')
    merge_.append(date_now)
    merge_.append(main_tabul)
    out_tab = '\n'.join(merge_)
    return out_tab
    #with open(f'report_{date_now}.txt', 'w') as f:
        #f.write(out_tab)
# In[69]:
def endpoint_health_check(cp_name,fe_name, cp_i,fe_i):
    fe_name = fe_name#get_value('FE_device_name=')
    cp_name = cp_name#get_value('CP_device_name=')
    #print(fe_name)
    #print(cp_name)
    fe_loopback0 = get_value(f'{fe_name}_loopback0=')
    fe_infos = {'name': fe_name, 'loopback0': fe_loopback0}
    cp_infos = {'name': cp_name, 'loopback0': ''}
    end_macs = import_instance_id_and_macs()
    #print(end_macs)
    no_ip_found_clean2, main_input_data = phase_2(end_macs,fe_infos,cp_infos)
    master_list = phase_3(main_input_data, no_ip_found_clean2, fe_infos,cp_infos)
    master_list = phase_4(master_list, fe_infos,cp_infos)
    output = final_phase(master_list,cp_infos, fe_infos,cp_i, fe_i)
    return output
# In[70]:
#fe_name = get_value('FE_device_name=')
#cp_name = get_value('CP_device_name=')
# In[77]:
cp_list = get_value('CP_device_list=')
fe_list = get_value('FE_device_list=')
final_tabulation = []
for cp_name in cp_list:
    final_tabulation.append('\n')
    final_tabulation.append('_'*120)
    cp_i = cp_list.index(cp_name) + 1
    for fe_name in fe_list:
        fe_i = fe_list.index(fe_name) + 1
        output = endpoint_health_check(cp_name,fe_name, cp_i, fe_i)
        final_tabulation.append(output)
        final_tabulation.append('\n')
final_report = '\n'.join(final_tabulation)
date_now = datetime.now().strftime("%m-%d-%y_%H-%M-%S") 
with open(f'report_{date_now}.txt', 'w') as f:
    f.write(final_report)
