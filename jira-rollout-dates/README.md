# Jira Rollout Date Updater

This script is a Node.js application that automates the process of updating rollout start and due dates for Jira issues. It splits the issues into multiple teams and calculates the due dates for each issue based on the start date, estimate, and working days.

## Prerequisites

Before you can use this script, make sure you have the following:

- Node.js installed on your machine.
- A Jira account with API access.
- Jira username and API token for authentication.

## Installation

1. Clone this repository or download the script to your local machine.

2. Install the required Node.js modules by running the following command in the project directory: `npm install`

## Usage

1. Run it using the following command: `node rollout-dates.js`

2. The script will ask for the necessary information and save it in the `.config` file

3. The script will fetch Jira issues based on a JQL query (you can modify the `jqlQuery` variable in the code).

4. It will display a list of issues and their summaries for your review.

5. The script will then split the issues into the specified number of teams and update rollout start and due dates.

6. It will print the details of each Jira issue updated.

7. The script will exit when all updates are complete.

## License

This script is provided under the MIT License. See the [LICENSE](LICENSE) file for details.

## Disclaimer

This script is provided as-is and is intended for educational and demonstration purposes. Use it responsibly and ensure it complies with your organization's policies and procedures.
