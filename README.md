# Development

## Install

    # Install pladder package in development mode -- i.e. link to this directory
    pip3 install -e .
    # Install systemd user service -- pladder-irc.service will be symlinked to the unit file in this directory
    # Service will be started on login or boot (which one depends on "user linger" setting)
    systemctl --user enable $PWD/pladder-irc.service
    # Also start systemd user service now
    systemctl --user start pladder-irc.service

## Check Status

    # Display status, process tree, stdout, etc
    systemctl --user status pladder-irc.service
    # Display full log for pladder
    journalctl --user -u pladder-irc.service -e

## Reload

    # For changes in pladder-irc.service unit file
    systemctl --user daemon-reload
    # For changes in Python code
    systemctl --user restart pladder-irc.service

## Remove

    # Stop systemd user service
    systemctl --user stop pladder-irc.service
    # Uninstall systemd user service (no automatic start)
    # Also removes link to development directory
    systemctl --user disable pladder-irc.service
