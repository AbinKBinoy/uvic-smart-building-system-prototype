# ============================================================================
# Smart Building Management System (BMS) Prototype
# ENGR 120 - University of Victoria
# ============================================================================

import machine
import time
import math
import network
import socket
from machine import Pin, ADC

# ============================================================================
# SECTION 1: PIN CONFIGURATION
# ============================================================================

led_lights  = Pin(18, Pin.OUT)
led_heating = Pin(16, Pin.OUT)
led_cooling = Pin(17, Pin.OUT)
pico_led    = Pin("LED", Pin.OUT)

motion_sensor = Pin(28, Pin.IN, Pin.PULL_DOWN)
temp_sensor   = ADC(26)
light_sensor  = ADC(27)

# ============================================================================
# SECTION 2: CONSTANTS AND STATE
# ============================================================================

THERMISTOR_R0 = 10000
THERMISTOR_T0 = 298.15
THERMISTOR_B  = 3960
LIGHT_THRESHOLD = 40000
DEBOUNCE_TIME = 10
PIR_CALIBRATION = 15

comfort_low  = 20.0
comfort_high = 24.0
preserve_low  = 15.0
preserve_high = 28.0

light_override = "auto"
hvac_override  = "auto"

temp_history = []
MAX_HIST = 30

event_log = []
MAX_LOG = 15

def add_event(msg):
    global event_log
    t = time.ticks_ms() // 1000
    m = t // 60
    s = t % 60
    stamp = str(m) + "m" + str(s) + "s"
    event_log.insert(0, stamp + " " + msg)
    if len(event_log) > MAX_LOG:
        event_log.pop()

# ============================================================================
# SECTION 3: SENSOR FUNCTIONS
# ============================================================================

def read_temperature():
    try:
        adc = temp_sensor.read_u16()
        if adc <= 0 or adc >= 65535:
            return None
        r = THERMISTOR_R0 * (65535.0 / adc - 1.0)
        tk = 1.0 / ((1.0 / THERMISTOR_T0) + (1.0 / THERMISTOR_B) * math.log(r / THERMISTOR_R0))
        return round(tk - 273.15, 1)
    except:
        return None

def read_light():
    adc = light_sensor.read_u16()
    if adc < LIGHT_THRESHOLD:
        return adc, "Dark"
    else:
        return adc, "Bright"

def read_motion():
    return motion_sensor.value()

# ============================================================================
# SECTION 4: CONTROL LOGIC
# ============================================================================

def control_hvac(temperature, is_occupied):
    global hvac_override
    if hvac_override == "heating":
        led_heating.on(); led_cooling.off(); return "Heating"
    elif hvac_override == "cooling":
        led_cooling.on(); led_heating.off(); return "Cooling"
    elif hvac_override == "off":
        led_heating.off(); led_cooling.off(); return "Off"
    if temperature is None:
        led_heating.off(); led_cooling.off(); return "Error"
    tl = comfort_low if is_occupied else preserve_low
    th = comfort_high if is_occupied else preserve_high
    if temperature < tl:
        led_heating.on(); led_cooling.off(); return "Heating"
    elif temperature > th:
        led_cooling.on(); led_heating.off(); return "Cooling"
    else:
        led_heating.off(); led_cooling.off(); return "Off"

def control_lighting(is_occupied, light_status):
    global light_override
    if light_override == "on":
        led_lights.on(); return "On"
    elif light_override == "off":
        led_lights.off(); return "Off"
    if is_occupied and light_status == "Dark":
        led_lights.on(); return "On"
    else:
        led_lights.off(); return "Off"

# ============================================================================
# SECTION 5: WI-FI
# ============================================================================

def setup_wifi():
    ssid = 'BMS_UVic'
    password = 'engr120bms'
    ap = network.WLAN(network.AP_IF)
    ap.config(essid=ssid, password=password)
    ap.active(True)
    while not ap.active():
        pass
    print('AP Active | IP:', ap.ifconfig()[0])
    return ap, ap.ifconfig()[0]

def setup_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
    s.settimeout(0.5)
    return s

# ============================================================================
# SECTION 6: WEB DASHBOARD
# ============================================================================

def build_page():
    return """<!DOCTYPE html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BMS Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0b1120;color:#e2e8f0;min-height:100vh}
.top{background:linear-gradient(135deg,#002754,#003976);padding:10px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1e3a5f}
.tl{display:flex;align-items:center;gap:10px}
.logo{width:34px;height:34px;border-radius:7px;background:#c63527;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;color:#fff}
.top h1{font-size:16px;font-weight:600;color:#fff}
.top p{font-size:10px;color:#7eb8e0}
.mbg{padding:5px 14px;border-radius:8px;font-size:11px;font-weight:700;letter-spacing:.5px}
.w{padding:14px 20px}
.sec{font-size:9px;color:#526580;text-transform:uppercase;letter-spacing:2px;margin:14px 0 8px;font-weight:700}
.sec:first-child{margin-top:0}
.main{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.col{display:flex;flex-direction:column;gap:12px}
.cd{background:#111827;border-radius:10px;padding:14px;border:1px solid #1e293b}
.lb{font-size:9px;color:#526580;text-transform:uppercase;letter-spacing:1px;margin-bottom:5px;font-weight:600}
.vl{font-size:32px;font-weight:700;line-height:1.1}
.un{font-size:15px;font-weight:400;color:#526580}
.sm{font-size:10px;color:#3e4c5e;margin-top:3px}
.row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #1e293b22}
.row:last-child{border:none}
.tg{font-size:10px;padding:3px 10px;border-radius:6px;font-weight:600}
.grn{background:#05966920;color:#34d399}.red{background:#dc262620;color:#f87171}
.gry{background:#47556920;color:#94a3b8}.ylw{background:#d9770620;color:#fbbf24}
.dot{width:6px;height:6px;border-radius:50%;display:inline-block;margin-right:6px}
.dg{background:#34d399}.dr{background:#f87171}.dy{background:#fbbf24}.db{background:#475569}
.ctl{display:flex;gap:5px;margin-top:8px}
.b{padding:8px 0;border-radius:7px;border:1px solid #1e293b;background:#0f172a;color:#526580;font-size:11px;cursor:pointer;font-weight:600;text-align:center;flex:1;transition:all .1s}
.b:active{transform:scale(0.95)}
.b.a{border-color:#38bdf8;color:#38bdf8;background:#0284c710}
.b.ag{border-color:#34d399;color:#34d399;background:#05966910}
.b.ar{border-color:#f87171;color:#f87171;background:#dc262610}
.b.ay{border-color:#fbbf24;color:#fbbf24;background:#d9770610}
.tc{display:flex;align-items:center;gap:2px}
.tb{width:30px;height:30px;border-radius:6px;border:1px solid #1e293b;background:#0f172a;color:#94a3b8;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center}
.tb:active{background:#1e293b}
.tv{font-size:14px;font-weight:600;min-width:48px;text-align:center}
.chart{display:flex;align-items:flex-end;gap:2px;height:80px;margin-top:6px;border-bottom:1px solid #1e293b44}
.bar{flex:1;min-width:3px;border-radius:2px 2px 0 0;transition:height .3s}
.cll{display:flex;justify-content:space-between;font-size:8px;color:#3e4c5e;margin-top:3px}
.evt{font-size:10px;color:#3e4c5e;padding:5px 0;border-bottom:1px solid #1e293b11}
.evt:last-child{border:none}
.evt b{color:#94a3b8;font-weight:500}
.ft{text-align:center;padding:12px;font-size:9px;color:#1e2a3b}
.pulse{animation:p 2s infinite}@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
.live{color:#34d399;font-size:9px;font-weight:600;letter-spacing:.5px}
.tr{display:flex;justify-content:space-between;align-items:center;margin-top:6px}
.trl{font-size:10px;color:#526580}
.sensors{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media(max-width:800px){.main{grid-template-columns:1fr}.sensors{grid-template-columns:1fr 1fr}}
@media(max-width:500px){.sensors{grid-template-columns:1fr 1fr}}
</style></head><body>
<div class="top">
<div class="tl">
<div class="logo">UV</div>
<div><h1>Smart BMS</h1><p>Building Management System &middot; Room 150</p></div>
</div>
<div style="display:flex;align-items:center;gap:12px">
<span class="pulse live">&#9679; LIVE</span>
<div class="mbg" id="bg" style="background:#47556920;color:#94a3b8">--</div>
</div>
</div>
<div class="w">
<div class="sec">Sensors</div>
<div class="sensors">
<div class="cd"><div class="lb">Temperature</div><div class="vl" id="tp">--<span class="un"> &deg;C</span></div><div class="sm" id="rn">--</div></div>
<div class="cd"><div class="lb">Ambient Light</div><div class="vl" id="li">--</div><div class="sm" id="lr">--</div></div>
<div class="cd"><div class="lb">Occupancy</div><div class="vl" id="mo">--</div><div class="sm">PIR sensor</div></div>
<div class="cd"><div class="lb">Mode</div><div class="vl" id="md2" style="font-size:20px">--</div><div class="sm" id="md3">--</div></div>
</div>
<div class="main">
<div class="col">
<div class="sec" style="margin-top:8px">System Status</div>
<div class="cd">
<div class="row"><span style="font-size:12px"><span class="dot" id="hd"></span>HVAC</span><span class="tg" id="hv">--</span></div>
<div class="row"><span style="font-size:12px"><span class="dot" id="ld"></span>Lighting</span><span class="tg" id="lg">--</span></div>
<div class="row"><span style="font-size:12px"><span class="dot" id="mdd"></span>Occupancy</span><span class="tg" id="oc">--</span></div>
</div>
<div class="sec">Lighting Control</div>
<div class="cd"><div class="ctl">
<div class="b" onclick="cmd('light_auto')" id="la">Auto</div>
<div class="b" onclick="cmd('light_on')" id="lo">On</div>
<div class="b" onclick="cmd('light_off')" id="lf">Off</div>
</div></div>
<div class="sec">HVAC Control</div>
<div class="cd"><div class="ctl">
<div class="b" onclick="cmd('hvac_auto')" id="ha">Auto</div>
<div class="b" onclick="cmd('hvac_heating')" id="hh">Heat</div>
<div class="b" onclick="cmd('hvac_cooling')" id="hc">Cool</div>
<div class="b" onclick="cmd('hvac_off')" id="ho">Off</div>
</div></div>
</div>
<div class="col">
<div class="sec" style="margin-top:8px">Comfort Thresholds (Occupied)</div>
<div class="cd">
<div class="tr"><span class="trl">Low</span><div class="tc"><div class="tb" onclick="adj('cl',-0.5)">-</div><div class="tv" id="tcl">20.0</div><div class="tb" onclick="adj('cl',0.5)">+</div></div></div>
<div class="tr"><span class="trl">High</span><div class="tc"><div class="tb" onclick="adj('ch',-0.5)">-</div><div class="tv" id="tch">24.0</div><div class="tb" onclick="adj('ch',0.5)">+</div></div></div>
</div>
<div class="sec">Preservation Thresholds (Unoccupied)</div>
<div class="cd">
<div class="tr"><span class="trl">Low</span><div class="tc"><div class="tb" onclick="adj('pl',-0.5)">-</div><div class="tv" id="tpl">15.0</div><div class="tb" onclick="adj('pl',0.5)">+</div></div></div>
<div class="tr"><span class="trl">High</span><div class="tc"><div class="tb" onclick="adj('ph',-0.5)">-</div><div class="tv" id="tph">28.0</div><div class="tb" onclick="adj('ph',0.5)">+</div></div></div>
</div>
<div class="sec">Temperature History</div>
<div class="cd"><div class="chart" id="ch"></div><div class="cll"><span>2 min ago</span><span>now</span></div></div>
</div>
<div class="col">
<div class="sec" style="margin-top:8px">Event Log</div>
<div class="cd" id="el" style="min-height:200px"><div class="evt">System started</div></div>
</div>
</div>
</div>
<div class="ft">Smart BMS Prototype &middot; ENGR 120 &middot; University of Victoria</div>
<script>
var tv={cl:20.0,ch:24.0,pl:15.0,ph:28.0};
function cmd(c){fetch('/?cmd='+c).then(function(){poll();});}
function adj(k,v){
tv[k]=Math.round((tv[k]+v)*10)/10;
document.getElementById('t'+k).textContent=tv[k].toFixed(1);
fetch('/?set_cl='+tv.cl+'&set_ch='+tv.ch+'&set_pl='+tv.pl+'&set_ph='+tv.ph).then(function(){poll();});
}
function poll(){
fetch('/data').then(function(r){return r.text();}).then(function(d){
var p=d.split('|');if(p.length<13)return;
var tmp=p[0],ls=p[1],lr=p[2],mt=p[3],hv=p[4],lg=p[5],lo=p[6],ho=p[7];
var cl=p[8],ch=p[9],pl=p[10],ph=p[11],hist=p[12],evts=p[13]||'';
var occ=mt=='1';
document.getElementById('tp').innerHTML=tmp+' <span class="un">&deg;C</span>';
document.getElementById('li').textContent=ls;
document.getElementById('lr').textContent='Raw: '+lr;
document.getElementById('mo').textContent=occ?'Yes':'No';
document.getElementById('md2').textContent=occ?'Occupied':'Unoccupied';
document.getElementById('md3').textContent=occ?'Comfort mode':'Preservation mode';
var b=document.getElementById('bg');
b.textContent=occ?'OCCUPIED':'UNOCCUPIED';
b.style.background=occ?'#05966920':'#dc262620';
b.style.color=occ?'#34d399':'#f87171';
document.getElementById('rn').innerHTML=occ?cl+'-'+ch+'&deg;C range':pl+'-'+ph+'&deg;C range';
var he=document.getElementById('hv');
he.textContent=hv;he.className='tg '+(hv=='Heating'?'red':hv=='Cooling'?'grn':'gry');
document.getElementById('hd').className='dot '+(hv=='Heating'?'dr':hv=='Cooling'?'dg':'db');
var le=document.getElementById('lg');
le.textContent=lg;le.className='tg '+(lg=='On'?'ylw':'gry');
document.getElementById('ld').className='dot '+(lg=='On'?'dy':'db');
var oe=document.getElementById('oc');
oe.textContent=occ?'Detected':'None';oe.className='tg '+(occ?'grn':'gry');
document.getElementById('mdd').className='dot '+(occ?'dg':'db');
['la','lo','lf'].forEach(function(x){document.getElementById(x).className='b';});
document.getElementById(lo=='auto'?'la':lo=='on'?'lo':'lf').className='b '+(lo=='auto'?'a':lo=='on'?'ay':'a');
['ha','hh','hc','ho'].forEach(function(x){document.getElementById(x).className='b';});
var hid=ho=='auto'?'ha':ho=='heating'?'hh':ho=='cooling'?'hc':'ho';
document.getElementById(hid).className='b '+(ho=='auto'?'a':ho=='heating'?'ar':ho=='cooling'?'ag':'a');
tv.cl=parseFloat(cl);tv.ch=parseFloat(ch);tv.pl=parseFloat(pl);tv.ph=parseFloat(ph);
document.getElementById('tcl').textContent=cl;
document.getElementById('tch').textContent=ch;
document.getElementById('tpl').textContent=pl;
document.getElementById('tph').textContent=ph;
var cv=document.getElementById('ch');cv.innerHTML='';
if(hist&&hist.length>0){
var pts=hist.split(',');var vals=[];
for(var i=0;i<pts.length;i++){var v=parseFloat(pts[i]);if(!isNaN(v))vals.push(v);}
if(vals.length>0){
var mn=Math.min.apply(null,vals)-2;var mx=Math.max.apply(null,vals)+2;
var rg=mx-mn;if(rg<1)rg=1;
for(var i=0;i<vals.length;i++){
var h=Math.max(4,((vals[i]-mn)/rg)*70);
var c=vals[i]>parseFloat(ch)?'#f87171':vals[i]<parseFloat(cl)?'#38bdf8':'#34d399';
var br=document.createElement('div');br.className='bar';
br.style.height=h+'px';br.style.background=c;
cv.appendChild(br);}}}
var el=document.getElementById('el');el.innerHTML='';
if(evts&&evts.length>0){
var ea=evts.split(',');
for(var i=0;i<ea.length;i++){
var ed=document.createElement('div');ed.className='evt';
var sp=ea[i].indexOf(' ');
if(sp>0){ed.innerHTML='<b>'+ea[i].substring(0,sp)+'</b> '+ea[i].substring(sp+1);}
else{ed.textContent=ea[i];}
el.appendChild(ed);}}
}).catch(function(){});}
setInterval(poll,2000);poll();
</script></body></html>"""


def build_data(temp, lval, lstat, mot, hvac, lght):
    t = str(temp) if temp is not None else "Err"
    m = "1" if mot else "0"
    h = ",".join([str(x) for x in temp_history]) if temp_history else ""
    e = ",".join(event_log) if event_log else ""
    return (t + "|" + lstat + "|" + str(lval) + "|" + m + "|" +
            hvac + "|" + lght + "|" + light_override + "|" + hvac_override + "|" +
            str(comfort_low) + "|" + str(comfort_high) + "|" +
            str(preserve_low) + "|" + str(preserve_high) + "|" + h + "|" + e)


# ============================================================================
# SECTION 7: REQUEST HANDLER
# ============================================================================

def handle_request(req):
    global light_override, hvac_override
    global comfort_low, comfort_high, preserve_low, preserve_high
    
    if "cmd=light_auto" in req:
        light_override = "auto"; add_event("Light > AUTO")
    elif "cmd=light_on" in req:
        light_override = "on"; add_event("Light > Manual ON")
    elif "cmd=light_off" in req:
        light_override = "off"; add_event("Light > Manual OFF")
    elif "cmd=hvac_auto" in req:
        hvac_override = "auto"; add_event("HVAC > AUTO")
    elif "cmd=hvac_heating" in req:
        hvac_override = "heating"; add_event("HVAC > Manual HEAT")
    elif "cmd=hvac_cooling" in req:
        hvac_override = "cooling"; add_event("HVAC > Manual COOL")
    elif "cmd=hvac_off" in req:
        hvac_override = "off"; add_event("HVAC > Manual OFF")
    
    if "set_cl=" in req:
        try:
            cl = req.split("set_cl=")[1].split("&")[0]
            ch = req.split("set_ch=")[1].split("&")[0]
            pl = req.split("set_pl=")[1].split("&")[0]
            ph = req.split("set_ph=")[1].split(" ")[0].split("&")[0]
            comfort_low = float(cl); comfort_high = float(ch)
            preserve_low = float(pl); preserve_high = float(ph)
            add_event("Thresh: C=" + cl + "-" + ch + " P=" + pl + "-" + ph)
        except:
            pass
    
    return "data" if "GET /data" in req else "page"


# ============================================================================
# SECTION 8: MAIN PROGRAM
# ============================================================================

def main():
    global temp_history
    
    print("=" * 50)
    print("Smart BMS - ENGR 120 - UVic")
    print("=" * 50)
    
    pico_led.on()
    led_lights.off(); led_heating.off(); led_cooling.off()
    add_event("System starting")
    
    print("PIR calibrating... 15s")
    time.sleep(PIR_CALIBRATION)
    print("PIR ready")
    add_event("PIR calibrated")
    
    ap, ip = setup_wifi()
    srv = setup_socket()
    dashboard = build_page()
    
    add_event("Wi-Fi active")
    print("\nhttp://" + ip)
    print("Wi-Fi: BMS_UVic / engr120bms")
    print("=" * 50)
    
    mot_state = False
    last_mot = 0
    last_print = time.ticks_ms()
    last_hist = time.ticks_ms()
    c_temp = None
    c_lval = 0
    c_lstat = "Bright"
    c_hvac = "Off"
    c_lght = "Off"
    prev_hvac = "Off"
    
    while True:
        ct = time.time()
        
        mv = read_motion()
        c_temp = read_temperature()
        c_lval, c_lstat = read_light()
        
        if mv == 1:
            if not mot_state:
                print(">>> OCCUPIED")
                add_event("Motion - OCCUPIED")
            mot_state = True
            last_mot = ct
        elif mv == 0:
            if mot_state and (ct - last_mot >= DEBOUNCE_TIME):
                print(">>> UNOCCUPIED")
                add_event("No motion - UNOCCUPIED")
                mot_state = False
        
        c_lght = control_lighting(mot_state, c_lstat)
        c_hvac = control_hvac(c_temp, mot_state)
        
        if c_hvac != prev_hvac:
            add_event("HVAC: " + c_hvac)
            prev_hvac = c_hvac
        
        if time.ticks_diff(time.ticks_ms(), last_hist) >= 4000:
            if c_temp is not None:
                temp_history.append(c_temp)
                if len(temp_history) > MAX_HIST:
                    temp_history.pop(0)
            last_hist = time.ticks_ms()
        
        try:
            conn, addr = srv.accept()
            req = str(conn.recv(1024))
            rt = handle_request(req)
            
            if rt == "data":
                resp = build_data(c_temp, c_lval, c_lstat, mot_state, c_hvac, c_lght)
                conn.send("HTTP/1.1 200 OK\r\n")
                conn.send("Content-Type: text/plain\r\n")
                conn.send("Content-Length: " + str(len(resp)) + "\r\n")
                conn.send("Connection: close\r\n\r\n")
                conn.send(resp)
            else:
                conn.send("HTTP/1.1 200 OK\r\n")
                conn.send("Content-Type: text/html\r\n")
                conn.send("Content-Length: " + str(len(dashboard)) + "\r\n")
                conn.send("Connection: close\r\n\r\n")
                for i in range(0, len(dashboard), 1024):
                    conn.send(dashboard[i:i+1024])
            conn.close()
        except OSError:
            pass
        except Exception as e:
            print("Web err:", e)
            try:
                conn.close()
            except:
                pass
        
        if time.ticks_diff(time.ticks_ms(), last_print) >= 2000:
            m = "OCC" if mot_state else "UNOCC"
            print("[" + m + "] T:" + str(c_temp) + "C L:" + c_lstat +
                  " HVAC:" + c_hvac + " Lght:" + c_lght)
            last_print = time.ticks_ms()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutdown")
        led_lights.off(); led_heating.off(); led_cooling.off(); pico_led.off()
