// Idempotently provision one least-privilege MongoDB account per service database.
const rootUsername = process.env.MONGO_ROOT_USERNAME;
const rootPassword = process.env.MONGO_ROOT_PASSWORD;
if (!rootUsername || !rootPassword) throw new Error("Missing MongoDB root credentials");
const admin = db.getSiblingDB("admin");
if (!admin.getUser(rootUsername)) {
  admin.createUser({ user: rootUsername, pwd: rootPassword, roles: ["root"] });
}

const users = [
  ["search_catalog", "search_app", process.env.SEARCH_MONGO_PASSWORD],
  ["analytic_scripts_db", "analytic_scripts_app", process.env.ANALYTIC_SCRIPTS_MONGO_PASSWORD],
  ["parsers_db", "parsers_app", process.env.PARSERS_MONGO_PASSWORD],
  ["messaging_db", "messaging_app", process.env.MESSAGING_MONGO_PASSWORD],
  ["notification_db", "notification_app", process.env.NOTIFICATION_MONGO_PASSWORD],
];

for (const [databaseName, username, password] of users) {
  if (!password) throw new Error(`Missing password for ${username}`);
  const target = db.getSiblingDB(databaseName);
  const roles = [{ role: "readWrite", db: databaseName }];
  if (target.getUser(username)) {
    target.updateUser(username, { pwd: password, roles });
  } else {
    target.createUser({ user: username, pwd: password, roles });
  }
}
