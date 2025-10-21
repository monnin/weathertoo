# TTF Fonts
apt install -y fonts-freefont-ttf

mkdir -p ~weather/weather/lib/fonts/truetype
cp /usr/share/fonts/truetype/freefont/FreeSans*.ttf ~weather/weather/lib/fonts/truetype

# Fixed Sized Fonts (100dpi versions)
apt install xfonts-100dpi
mkdir -p ~weather/weather/lib/fonts/fixed/100dpi
(cd ~weather/weather/lib/fonts/fixed/100dpi; python3 ~weather/weather/bin/convert-fonts.py helv*.pcf.gz)

# Fixed Sized Fonts (75dpi versions)
apt install xfonts-75dpi
mkdir -p ~weather/weather/lib/fonts/fixed/75dpi
(cd ~weather/weather/lib/fonts/fixed/75dpi; python3 ~weather/weather/bin/convert-fonts.py helv*.pcf.gz)
