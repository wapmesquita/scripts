const axios = require('axios');
const moment = require('moment');
const business = require('moment-business');
const fs = require('fs');
const readlineSync = require('readline-sync');

// Configuration file path
const configFilePath = './.config';

var startDateFieldName;
var dueDateFieldName;
var jiraHost;
var username;
var token;
var jqlQuery;
var numTeams = 1; // Number of teams to split the rollout
var startDate; // Change this to your desired start date

// Function to get Jira issues

async function getJiraIssues(username, token, jqlQuery) {
    try {
        console.log("Query", encodeURIComponent(jqlQuery));
        console.log(username, token);
        const response = await axios.get(
            `${jiraHost}/rest/api/3/search?jql=${encodeURIComponent(jqlQuery)}&maxResults=100&validateQuery=strict`,
            {
                headers: {
                    'Accept': 'application/json',
                    'Authorization': `Basic ${Buffer.from(`${username}:${token}`).toString('base64')}`
                }
            }
        );
        return response.data.issues;
    } catch (error) {
        console.error('Error fetching Jira issues:', error.message);
        process.exit(1);
    }
}

// Function to update rollout dates for a team
async function updateRolloutDates(issues, username, token, startDateFieldName, dueDateFieldName, rolloutDateStart) {
    var startDate = moment(rolloutDateStart);
    for (let i = 0; i < issues.length; i++) {
        const issue = issues[i];
        const estimateDays = (issue.fields.timeestimate || 5 / 60 / 60 / 8) - 1;
        const payload = {
            fields: {}
        };
        payload.fields[startDateFieldName] = startDate.format('YYYY-MM-DD');
        const dueDate = business.addWeekDays(startDate, estimateDays);
        payload.fields[dueDateFieldName] = dueDate.format('YYYY-MM-DD');

        try {
            const response = await axios.put(
                `${jiraHost}/rest/api/3/issue/${issue.key}?overrideScreenSecurity=false&overrideEditableFlag=false`,
                payload,
                {
                    headers: {
                        'Accept': 'application/json',
                        'Authorization': `Basic ${Buffer.from(`${username}:${token}`).toString('base64')}`,
                        'Content-Type': 'application/json'
                    }
                }
            );
            console.log(`[INFO] Jira ${issue.key} updated.\nResponse: ${JSON.stringify(response.data)}\n======`);
        } catch (error) {
            console.error(`Error updating Jira issue ${issue.key}:`, error.message);
        }

        startDate = business.addWeekDays(dueDate, 1);
    }
}

function readConfig() {
    if (fs.existsSync(configFilePath)) {
        const config = JSON.parse(fs.readFileSync(configFilePath));
        jiraHost = config.jiraHost || jiraHost;
        startDateFieldName = config.startDateFieldName || startDateFieldName;
        dueDateFieldName = config.dueDateFieldName || dueDateFieldName;
        numTeams = config.numTeams || numTeams;
        startDate = config.startDate || startDate;
        token = config.token || token;
        username = config.username || username;
        jiraHost = config.jiraHost || jiraHost;
        jqlQuery = config.jqlQuery || jqlQuery;
    }

}

// Function to save configuration to the file
function saveConfig() {
    const config = {
        startDateFieldName,
        dueDateFieldName,
        numTeams,
        startDate,
        jqlQuery,
        token,
        jiraHost,
        username
    };
    fs.writeFileSync(configFilePath, JSON.stringify(config, null, 2));
}

// Function to set or update the variables interactively
function configureVariables() {
    jiraHost = readlineSync.question(`Enter jira host e.i. https://company.atlassian.net (${jiraHost}): `) || jiraHost;
    startDateFieldName = readlineSync.question(`Enter Start Date field name (${startDateFieldName}): `) || startDateFieldName;
    dueDateFieldName = readlineSync.question(`Enter Due Date field name (${dueDateFieldName}): `) || dueDateFieldName;
    numTeams = readlineSync.question(`Enter Number of teams (${numTeams}): `) || numTeams;
    startDate = readlineSync.question(`Enter Start Date YYYY-MM-DD (${startDate}): `) || startDate;
    jqlQuery = readlineSync.question(`Enter the Jira Query to get the issues (${jqlQuery}): `) || jqlQuery;

    // Prompt for the Jira username and token separately, without displaying the token
    username = readlineSync.question(`Enter Jira username/email (${username}): `) || username;
    token = readlineSync.question('Enter Jira Token: ', {
        hideEchoBack: true,
        mask: '*',
    }) || token;

    saveConfig();
}


// Main function
async function main() {
    readConfig();

    configureVariables();

    console.log('Start Date Field Name:', startDateFieldName);
    console.log('Due Date Field Name:', dueDateFieldName);
    console.log('Number of Teams:', numTeams);
    console.log('Start Date:', startDate);
    console.log('Jira username:', username);
    console.log('Jira hostname:', jiraHost);

    const issues = await getJiraIssues(username, token, jqlQuery);

    // Print the list of issues
    console.log('List of Issues:');
    issues.forEach((issue, index) => {
        console.log(`${index + 1}. ${issue.key} - ${issue.fields.summary}`);
    });

    // Ask for confirmation before proceeding
    const confirmation = await askForConfirmation();
    if (confirmation.toLowerCase() !== 'yes') {
        console.log('Script aborted.');
        return;
    }

    const teams = [];

    // Initialize teams
    for (let i = 0; i < numTeams; i++) {
        teams.push([]);
    }

    // Split issues into teams
    for (let i = 0; i < issues.length; i++) {
        const teamIndex = i % numTeams;
        teams[teamIndex].push(issues[i]);
    }

    // Update rollout dates for each team
    for (const team of teams) {
        await updateRolloutDates(team, username, token, startDateFieldName, dueDateFieldName, startDate);
    }
}

// Function to ask for confirmation
function askForConfirmation() {
    return new Promise((resolve) => {
        const rl = require('readline').createInterface({
            input: process.stdin,
            output: process.stdout
        });

        rl.question('Do you want to proceed with the update? (yes/no): ', (answer) => {
            rl.close();
            resolve(answer);
        });
    });
}

// Execute the main function
main().catch((error) => {
    console.error('An error occurred:', error.message);
});
