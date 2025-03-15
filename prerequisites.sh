#!/bin/sh

# Temporary username to create
USERNAME="treeostempus3rx01_script"

# Cancel any pending rpm-ostree transaction
rpm-ostree cancel

# Check if user already exists, if not, create it
if ! id "$USERNAME" &>/dev/null; then
    useradd -m -s /bin/bash "$USERNAME"
    passwd -d "$USERNAME"
fi

# Add user to the wheel group (administrators)
usermod -aG wheel "$USERNAME"

# Install necessary packages
rpm-ostree install steam-devices openrgb-udev-rules gnome-shell-extension-blur-my-shell \
  gnome-shell-extension-dash-to-panel gnome-shell-extension-dash-to-dock \
  gnome-shell-extension-appindicator openbox -r

# Double confirmation before proceeding with user deletion
echo "WARNING: This script will delete all users except '$USERNAME' from the system."
read -p "Type 'yes' to continue: " confirmation
if [ "$confirmation" != "yes" ]; then
    echo "Operation cancelled."
    exit 1
fi

read -p "This action is irreversible. Type 'CONFIRM' to proceed: " second_confirmation
if [ "$second_confirmation" != "CONFIRM" ]; then
    echo "Operation cancelled."
    exit 1
fi

# Apply global configurations via dconf
mkdir -p /etc/dconf/db/local.d/

cat <<EOF > /etc/dconf/db/local.d/00-global-settings
[org/gnome/shell]
favorite-apps=['org.mozilla.firefox.desktop', 'org.mozilla.Thunderbird.desktop', 'org.gnome.Nautilus.desktop', 'org.libreoffice.LibreOffice.writer.desktop', 'org.gnome.Software.desktop']
enabled-extensions=['appindicatorsupport@rgcjonas.gmail.com','blur-my-shell@aunetx']
welcome-dialog-last-shown-version='4294967295'

[org/gnome/desktop/wm/preferences]
button-layout=':minimize,maximize,close'

[org/gnome/desktop/peripherals/touchpad]
tap-to-click=true

[org/gtk/settings/file-chooser]
sort-directories-first=true

[org/gtk/gtk4/settings/file-chooser]
sort-directories-first=true
EOF

# Ensure no syntax errors (remove accidental double commas)
sed -i 's/, ,/,/g' /etc/dconf/db/local.d/00-global-settings

# Update dconf database
dconf update

# Create script to remove all other users at first login
cat <<'EOF' > /home/$USERNAME/clean_users.sh
#!/bin/sh

CURRENT_USER=$(whoami)

for user in $(awk -F: '{print $1}' /etc/passwd | grep -vE "^(root|$CURRENT_USER)$"); do
    userdel -r "$user"
    echo "Deleted user: $user"
done

# Remove the script after execution
rm -- "$0"
EOF

chmod +x /home/$USERNAME/clean_users.sh

# Execute clean_users.sh automatically on the first login
if ! grep -q "clean_users.sh" /home/$USERNAME/.bashrc; then
    echo "bash ~/clean_users.sh" >> /home/$USERNAME/.bashrc
fi
