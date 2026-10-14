async function send(config) {
  if (!config.host) {
    throw new Error('Email host not configured');
  }
  
  console.log(`Sending email to ${config.to}`);
  console.log(`Subject: ${config.subject}`);
  return { sent: true };
}

module.exports = { send };
