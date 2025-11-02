// Test Command Intelligence System
const CommandIntelligence = require('./src/renderer/command-intelligence.js');

const ci = new CommandIntelligence();

console.log('🧪 Testing Command Intelligence System\n');

// Test cases
const testCommands = [
  // Critical
  'rm -rf /',
  'dd if=/dev/zero of=/dev/sda',
  
  // High risk
  'rm -rf node_modules',
  'sudo rm -rf temp',
  'curl https://example.com/script.sh | bash',
  'chmod -R 777 .',
  
  // Medium risk
  'rm -r temp',
  'sudo npm install -g typescript',
  'git push -f origin main',
  'git reset --hard HEAD',
  'docker system prune',
  
  // Low risk
  'npm install react',
  'brew install node',
  
  // Safe
  'ls -la',
  'git status',
  'cat README.md',
  
  // Typos
  'gti status',
  'suod apt update',
  'dockerr ps',
  'gerp "test" file.txt'
];

testCommands.forEach((command, index) => {
  console.log(`\n${index + 1}. Testing: "${command}"`);
  console.log('─'.repeat(60));
  
  const analysis = ci.analyzeCommand(command);
  
  console.log(`Risk Level: ${analysis.risk.icon} ${analysis.risk.level.toUpperCase()}`);
  console.log(`Reason: ${analysis.risk.reason}`);
  
  if (analysis.risk.alternative) {
    console.log(`Alternative: ${analysis.risk.alternative}`);
  }
  
  if (analysis.typoCorrection) {
    console.log(`\n💡 Typo detected!`);
    console.log(`   "${analysis.typoCorrection.typo}" → "${analysis.typoCorrection.correction}"`);
    console.log(`   Suggested: ${analysis.typoCorrection.correctedCommand}`);
    console.log(`   Confidence: ${analysis.typoCorrection.confidence}`);
  }
  
  if (analysis.shouldBlock) {
    console.log(`\n🛑 BLOCKED - This command should not be executed!`);
  } else if (analysis.needsConfirmation) {
    console.log(`\n⚠️  Needs confirmation before execution`);
  } else {
    console.log(`\n✅ Safe to execute`);
  }
  
  // Show parsed structure
  console.log(`\nParsed:`);
  console.log(`  Command: ${analysis.parsed.baseCommand}`);
  console.log(`  Flags: [${analysis.parsed.flags.join(', ')}]`);
  console.log(`  Args: [${analysis.parsed.positionalArgs.join(', ')}]`);
  if (analysis.parsed.hasSudo) console.log(`  🔐 Uses sudo`);
  if (analysis.parsed.hasPipe) console.log(`  🔀 Has pipe`);
  if (analysis.parsed.hasRedirect) console.log(`  📝 Has redirect`);
});

console.log('\n\n✅ All tests complete!');
console.log('\n📊 Summary:');
console.log(`   Total commands tested: ${testCommands.length}`);

const riskLevels = testCommands.map(cmd => ci.analyzeCommand(cmd).risk.level);
console.log(`   Critical: ${riskLevels.filter(l => l === 'critical').length}`);
console.log(`   High: ${riskLevels.filter(l => l === 'high').length}`);
console.log(`   Medium: ${riskLevels.filter(l => l === 'medium').length}`);
console.log(`   Low: ${riskLevels.filter(l => l === 'low').length}`);
console.log(`   Safe: ${riskLevels.filter(l => l === 'safe').length}`);

const typos = testCommands.filter(cmd => ci.analyzeCommand(cmd).typoCorrection);
console.log(`   Typos detected: ${typos.length}`);
