#!/usr/bin/env bash
# install.sh  v2
set -euo pipefail

INSTALL_DIR="/usr/local/wedge100-nos"
ACCTON_DIR="/usr/local/accton"
SERVICE_DIR="/etc/systemd/system"
APACHE_SITES="/etc/apache2/sites-available"
SNMPD_CONF="/etc/snmp/snmpd.conf"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
err()  { echo -e "${RED}  ✗${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && err "root 권한으로 실행하세요: sudo bash install.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""; echo "══ Wedge 100 NOS 설치 v2 ══"; echo ""

echo "[1/9] 소스 설치..."
mkdir -p "$INSTALL_DIR" /var/lib/wedge100-nos
cp -r "$SCRIPT_DIR/wedge100"    "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/snmp_agents" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/scripts"     "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/webui"       "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/db"          "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR"/snmp_agents/*.py "$INSTALL_DIR"/scripts/*.py "$INSTALL_DIR"/wedge100/daemons/*.py
ok "소스 → $INSTALL_DIR"

echo "[2/9] Python 패키지..."
pip3 install click mysql-connector-python --break-system-packages -q 2>/dev/null || \
pip3 install click mysql-connector-python -q 2>/dev/null || warn "pip3 실패 - 수동 설치 필요"
ok "Python 패키지"

echo "[3/9] 시스템 패키지..."
export DEBIAN_FRONTEND=noninteractive
command -v apache2 &>/dev/null || apt-get install -y apache2 php php-mysql libapache2-mod-php -q
command -v mysql   &>/dev/null || { apt-get install -y mysql-server -q; systemctl enable --now mysql; }
command -v snmpd   &>/dev/null || apt-get install -y snmpd snmp -q
command -v lldpcli &>/dev/null || { apt-get install -y lldpd -q; systemctl enable --now lldpd; }
if ! command -v vtysh &>/dev/null; then
  curl -s https://deb.frrouting.org/frr/keys.asc | gpg --dearmor -o /usr/share/keyrings/frrouting.gpg
  echo "deb [signed-by=/usr/share/keyrings/frrouting.gpg] https://deb.frrouting.org/frr $(lsb_release -sc) frr-stable" > /etc/apt/sources.list.d/frr.list
  apt-get update -q && apt-get install -y frr frr-pythontools -q
  sed -i 's/^bgpd=no/bgpd=yes/' /etc/frr/daemons 2>/dev/null || true
  systemctl enable --now frr
fi
ok "시스템 패키지"

echo "[4/9] MySQL DB..."
if ! mysql -u root -e "SHOW DATABASES LIKE 'wedge100nos';" 2>/dev/null | grep -q wedge100nos; then
  mysql -u root < "$INSTALL_DIR/db/schema.sql"
  ok "DB 초기화 완료"
else warn "DB 이미 존재 (스킵)"; fi

echo "[5/9] CLI 링크..."
cat > /usr/local/bin/wedge << 'EOF'
#!/usr/bin/env bash
export PYTHONPATH=/usr/local/wedge100-nos
exec python3 /usr/local/wedge100-nos/wedge100/cli/main.py "$@"
EOF
chmod +x /usr/local/bin/wedge
ok "wedge CLI"

echo "[6/9] systemd 서비스..."
cp "$INSTALL_DIR/scripts/wedge100-nos.service" "$SERVICE_DIR/"
cp "$INSTALL_DIR/scripts/wedge100-led.service" "$SERVICE_DIR/"
systemctl daemon-reload
systemctl enable wedge100-nos wedge100-led
ok "wedge100-nos, wedge100-led 서비스 등록"

echo "[7/9] Apache WebUI..."
cp "$INSTALL_DIR/webui/wedge100-nos.conf" "$APACHE_SITES/"
a2ensite wedge100-nos 2>/dev/null || true
a2dissite 000-default 2>/dev/null || true
cat > /etc/sudoers.d/wedge100-www << 'SUDO'
www-data ALL=(root) NOPASSWD: /usr/local/bin/wedge
www-data ALL=(root) NOPASSWD: /usr/bin/python3 /usr/local/wedge100-nos/wedge100/daemons/led_daemon.py
SUDO
chmod 440 /etc/sudoers.d/wedge100-www
chown -R www-data:www-data "$INSTALL_DIR/webui"
systemctl restart apache2
ok "Apache WebUI"

echo "[8/9] SNMP..."
if [[ -f "$SNMPD_CONF" ]] && ! grep -q "wedgePortStatus" "$SNMPD_CONF"; then
  cat "$INSTALL_DIR/snmp_agents/snmpd_wedge100.conf" >> "$SNMPD_CONF"
  systemctl restart snmpd 2>/dev/null || true
  ok "SNMP 설정 추가"
else warn "SNMP 스킵"; fi

echo "[9/9] Accton 바이너리 확인..."
[[ -d "$ACCTON_DIR/bin" ]] && ok "Accton: $ACCTON_DIR/bin" || warn "accton.zip 을 /usr/local/accton 에 압축 해제 필요"

IP=$(hostname -I | awk '{print $1}')
echo ""; echo "══ 설치 완료! ══"
echo "  WebUI  → http://$IP/"
echo "  CLI    → wedge --help"
echo "  시작   → sudo systemctl start wedge100-nos wedge100-led"
