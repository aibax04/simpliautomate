# AWS Deployment Guide for Simplii

This guide explains how to deploy the Simplii automation platform to an AWS EC2 instance.

## Prerequisites

You should have the following "Supportnest credentials":
1.  **Server IP Address** (e.g., `3.14.159.26`)
2.  **Username** (usually `ubuntu` for Ubuntu AMIs, or `ec2-user` for Amazon Linux)
3.  **RSA Private Key File** (e.g., `key.pem`)

## Step 1: Prepare Your Environment

1.  **Locate your Key File**: Ensure you know the path to your `.pem` file.
    *   *Windows Note*: You might need to restrict permissions on this key file if using OpenSSH, but standard Windows `ssh` often handles it.

2.  **Configure `.env`**:
    Ensure you have a `.env` file in your project root with your production secrets.
    ```ini
    DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
    GEMINI_API_KEY=your_key_here
    SECRET_KEY=your_secret
    ...
    ```

## Step 2: Upload Code to Server

Open PowerShell or Command Prompt in the `simplii` folder and run the following command to copy your files to the server.

Replace `path\to\key.pem` with your actual key path, and `IP_ADDRESS` with the server IP.

```powershell
# Copy all files to a 'simplii' folder on the server
scp -r -i "path\to\key.pem" . ubuntu@IP_ADDRESS:~/simplii/
```

> **Note**: If your username is not `ubuntu`, replace it with `ec2-user` or `admin` as provided.

## Step 3: Run Deployment Script

Connect to the server via SSH:

```powershell
ssh -i "path\to\key.pem" ubuntu@IP_ADDRESS
```

Once logged in, run the following commands to start the automated deployment:

```bash
# Go to the directory
cd simplii

# Make the script executable
chmod +x deploy_aws.sh

# Run the deployment script
./deploy_aws.sh
```

## Step 4: Verify Deployment

1.  **Check Status**:
    ```bash
    sudo systemctl status simplii
    ```
    It should say `active (running)`.

2.  **Access the App**:
    Open your browser and visit `http://YOUR_SERVER_IP`.
    You should see the application running.

## Troubleshooting

-   **Database**: If using a local SQLite DB, it will be on the server disk. For production, ensure `DATABASE_URL` points to your RDS or hosted database.
-   **Security Groups**: Ensure your AWS Security Group allows **Inbound Traffic** on ports:
    -   `22` (SSH)
    -   `80` (HTTP)
-   **Logs**: To see application logs:
    ```bash
    journalctl -u simplii -f
    ```
