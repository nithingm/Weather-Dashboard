# Real-Time Weather Data Streaming to Azure Event Hub and Microsoft Fabric

## Project Objective
Build a fully **serverless weather streaming pipeline** that fetches live weather data every 60 seconds from [WeatherAPI](https://www.weatherapi.com/), processes and flattens it, and streams it to **Azure Event Hub**, then stores it in **Microsoft Fabric Eventhouse** via **EventStream** for real-time querying using **KQL**.

This is ideal for real-time dashboards, anomaly detection, or downstream analytics.

Inspired by this [youtube series.](https://www.youtube.com/watch?v=okrKwdn9Z34&list=PLrG_BXEk3kXyEV0dzmAN-49tLrQsM0jUa)
---

## Architecture Overview

```text
WeatherAPI --> Azure Function (Timer Trigger) --> Azure Event Hub --> Microsoft Fabric EventStream --> Eventhouse (KQL DB) --> Power BI Dashboard
```

---

## Prerequisites

- Azure Subscription (I used a student account. If you don't have that, please use a free trial with a new account)
- WeatherAPI Key (https://www.weatherapi.com/). Sign up and obtain a login key (up to 1m API calls a month for free!)
- Visual Studio Code with Azure Functions extension installed
- Python 3.x
- Microsoft Fabric access (Again, feel free to use a free trial here)
- Power BI Desktop (latest version)

---

## Azure Resources Setup

### 1. Create a Resource Group
- On the azure website, create a resource group. I called `rg-WeatherStream`
  
### 2. Create Azure Event Hub
- Namespace: `weatherstreamingnamespace`  # This is the name I used, please use any acceptable name of your choice 
- Event Hub Name: `weatherstreameventhub` # This is the name I used, please use any acceptable name of your choice

Create a **Shared Access Policy** under the Event Hub with:
- Name: `fabric-listen`                   # This is the name I used, please use any acceptable name of your choice
- Permissions: Listen only                # 'Listen only' is all we need for this

### 3. Create Azure Key Vault
- Name: `kv-weather-streaming-311`        # This is the name I used, please use any acceptable name of your choice
- Add a secret: `weatherapikey`           # This is the name I used, please use any acceptable name of your choice
- Value: Your WeatherAPI key

### 4. Create Azure Function App
You can create this from the Azure Portal.

---

## Local Azure Function App Setup (VS Code)

### Step 1: Sign in to Azure and Prepare VS Code
- Install the **Azure Functions Extension**
- Sign in to your Azure account

### Step 2: Create Function Project
- Click Azure Icon → Workspace → Create Function Project
- Language: `Python`
- Trigger: `Timer Trigger`
- Function Name: `weatherapifunction`
- Schedule (CRON): `*/60 * * * * *` (every 60 seconds)  # Modify this according to your requirements

### Step 3: Enable Managed Identity for Function App
- Go to: Function App → Settings → Identity → Set `Status: On`

### Step 4: Assign IAM Roles

#### a. **Event Hub**
- Role: `Azure Event Hubs Data Sender`
- Assigned to: Managed Identity of the Function App

#### b. **Key Vault**
- Role: `Key Vault Secrets User`
- Assigned to: Managed Identity of the Function App

### Step 5: Update `requirements.txt`
```txt
azure.eventhub
azure.identity
azure.keyvault.secrets
requests
```

### Step 6: Add Function Logic
Edit `function_app.py` to:
- Fetch the WeatherAPI key securely from Key Vault
- Fetch current weather, air quality, forecast, and alerts
- Flatten the JSON
- Send the data to Event Hub

> Full Python code is provided in the repository folder; Using `DefaultAzureCredential()` for secure authentication to both services.
> Just copy the code across to start with. You can modify it to your needs after getting this running.

### Step 7: Deploy to Azure
- In VS Code, right-click the workspace folder → `Deploy to Function App`
- Select your Function App

✅ Done! Your function is now running every 30 seconds and sending JSON data to Event Hub.

---

## Microsoft Fabric Integration

### Step 1: Create Fabric Workspace
- Name: `weather-fabric-ws`         # This is the name I used, please use any acceptable name of your choice

### Step 2: Add Eventhouse
- Go to workspace → `+ New` → Select **Eventhouse**
- Name this appropriately.
  
### Step 3: Add EventStream
- Go to workspace → `+ New` → Select **EventStream**
- Add Source → `Event Hub`
  - Paste **Namespace** and **Event Hub name**
  - **Authentication**: Shared Access Key
  - Use `fabric-listen` shared access policy or the policy you've made before in Step 2
  - Data Format: `JSON`

### Step 4: Add Destination
- Click Destination Node → `+ Destination` → Select **Eventhouse**
- Destination Name: `weather-target`
- Choose Eventhouse and KQL DB created earlier
- Table Name: `weather-table`                        # This is the name I used, please use any acceptable name of your choice
- Data Format: `JSON`
- Check "Activate ingestion after adding the data source"
- Save and **Publish** the stream

✅ Data is now flowing live into Microsoft Fabric!

### Step 5: Query the Data
- Go to Fabric → Workspace → Eventhouse → Table → `weather-table`
- Click `⋮` (three dots) → `Query with code`
- Run:
```kql
weather-table
| take 100
```
or 
```kql
weather-table
| count
```

✅ You should see live data from WeatherAPI inside your KQL database.

---

## 📊 Power BI Dashboard Setup

### Step 1: Download and Open the Dashboard
- Download the `.pbix` file from this GitHub repository
- Open it in **Power BI Desktop**

### Step 2: Update the KQL Connection
- Go to: `Table View` → Select a table → Click `Edit Query`
- Click `Advanced Editor`
- Change the following:
  - Eventhouse URL
  - KQL Database name
  - Table name
- Confirm and apply changes
- Click `Refresh` to load updated data

### Step 3: Publish to Power BI Service
- Click `Publish` and choose the workspace you created
- The dashboard and semantic model will appear under your resource group

---

## Ὢ8 Setting Up Alerts with KQL

### Step 1: Create a KQL Queryset
- Go to: `Eventhouse` → `New KQL Queryset`
- Name: `alerts`
- Source: Your Eventhouse database

### Step 2: Add Alert Logic
```kql
['weather-table']
| where alerts != '[]'  // filter for records where alert condition exists
| extend AlertValue = tostring(alerts) // extract alerts as a string
| summarize LastTriggered = max(EventProcessedUtcTime) by AlertValue
| join kind = leftanti (
    ['weather-table']
    | where alerts != '[]'
    | extend AlertValue = tostring(alerts)
    | summarize LastTriggered = max(EventProcessedUtcTime) by AlertValue
    | where LastTriggered < ago(4m)
) on AlertValue
```

✅ This filters out any outdated alerts and gives you only **currently active ones**.

---

## Conclusion
You've built a **fully serverless, secure, and real-time data streaming pipeline** from WeatherAPI → Azure Function → Event Hub → Fabric → KQL Database → Power BI.

> This sets the foundation for building real-time **dashboards**, **alerts**, and **analytics pipelines**.

---

