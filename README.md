ubootwrite
==========
Is a simple python tool that uploads binary images to the RAM of linux systems running the U-Boot bootloader (e.g. for OpenWRT) via the serial port. It works in cases where no transfer via alternate methods (XMODEM/TFTP/BOOTM/etc.) can be made. ubootwrite has a high overhead, as the binary file is converted to ASCII and sent in 32Bit chucks, so transferring larger amounts of data can be really slow.
The original author is "pgid69" and the original source is the [OpenWRT forum](https://forum.openwrt.org/viewtopic.php?pid=183315#p183315). The initial commit is the original version found in the forum and "pgid69" states the tool is based on [brntool](https://github.com/rvalles/brntool). As I did some adjustments for uploading data onto the Arcadyan ARV752DPW22 (Easybox 803A) and it did not seem to have a permanent home, I "forked" the code here...

This version of ubootwrite has been modified by ???[^0] to provide support for the vendor-modified [Das U-Boot loader](https://www.denx.de/wiki/U-Boot) as used by the Cisco Meraki MR33 Access Points. The U-Boot command prompt on these APs can only be reached if the ```xyzzy``` string ([```CONFIG_AUTOBOOT_STOP_STR```](https://source.denx.de/u-boot/u-boot/-/blob/master/doc/README.autoboot#L80)) is send during boot.  
This version won't work with regular U-Boot bootloaders, only with Cisco modified bootloader as used in Meraki MR33 APs.

Cisco Meraki MR33 Access Points are known to have two different versions of bootloaders:
* ```U-Boot 2012.07-g97ab7f1 [local,local] (Oct 06 2016 - 13:07:25)```  
  => Supported.
* ```U-Boot 2017.07-RELEASE-g78ed34f31579 (Sep 29 2017 - 07:43:44 -0700)```  
  => Not supported. No known method exists to enter the U-Boot command prompt, if possible at all.

Please verify which version you have prior to running this script. Cisco Meraki APs are known to auto-update without prior warning.  
You risk permanently bricking your device if you try to enter the U-Boot command prompt on a device running any other version then ```U-Boot 2012.07-g97ab7f1```.  
If ```'Secure boot NOT enabled! Blowing fuses... Resetting now.'``` is printed on the serial console, it is too late...

source of modified version:
[https://drive.google.com/drive/folders/1goSM3qgRjna2DFZbhrlLAyfQr4iBwqr_](https://drive.google.com/drive/folders/1goSM3qgRjna2DFZbhrlLAyfQr4iBwqr_)

Ported from Python2 to Python3 by @sebastiaanv3  
Requires at least Python 3.6  
Tested only using Python 3.9.10 and Python 3.10.2

License
=======
Basically it can only be [GPLv3](http://opensource.org/licenses/GPL-3.0), because [brntool](https://github.com/rvalles/brntool) is. See [LICENSE.md](LICENSE.md).

Prerequisites
=============
Requires [pyserial](https://pypi.org/project/serial/)
`$ pip install -r requirements.txt`

Overview
========
Use Python3 (3.6+) to run the tool: ```python ubootwrite.py [OPTIONS]```.  
**Options:**  
* ```--verbose``` - Be verbose.  
* ```--serial``` - The serial port to write to, e.g. ```--serial=/dev/ttyUSB2```. It will open it with 115200 Baud, 8 data bits, one stop bit.  
* ```--write``` - The file to transfer to RAM, e.g. ```--write=openwrt-squashfs.image```.  
* ```--addr``` - The RAM start address to write to, e.g. ```--addr=0x80050000```.  
* ```--size``` - The number of bytes to transfer, e.g. ```--size=12345```. Omit to transfer the whole file.

**An example for a full command line could be:**  
```python ubootwrite.py --serial=/dev/ttyUSB0 --write=mr33-uboot.bin```  
This can take a looong time (about 3 minutes). Be patient. Once the data is loaded in RAM, the script will automatically initiate a reboot.  

FAQ
===
**Q:** I'm on linux and I can not access the serial port somehow...  
**A:** You might need to add your USERNAME to the dialout group: ```sudo usermod -a -G dialout USERNAME``` or use sudo.  

I found a bug or have a suggestion
==================================
The best way to report a bug or suggest something is to post an issue on GitHub. Try to make it simple, but descriptive and add ALL the information needed to REPRODUCE the bug.  
**"Does not work" is not enough!**

[^0]: Please let me know if it was you or you do know whom did so proper credits can be given.
