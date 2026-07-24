/**
 * generate_sample.js
 *
 * Generates a sample Excel file (sample.xlsx) with random Chinese names,
 * GitHub IDs, and departments for testing the Git Commit Statistics Dashboard.
 *
 * Usage: node generate_sample.js
 * Output: sample.xlsx in the current directory
 *
 * After generating, replace the sample data with your real team's information.
 */

const XLSX = require('xlsx');

// Sample data: GitHub ID, Real Name, Department, Alias(es) (comma-separated)
// Replace this array with your actual team members
const members = [
  { githubId: 'zhangsan', realName: '张三', department: '后端组', aliases: 'zhangsan_dev' },
  { githubId: 'lisi', realName: '李四', department: '后端组', aliases: '' },
  { githubId: 'wangwu', realName: '王五', department: '后端组', aliases: '' },
  { githubId: 'zhaoliu', realName: '赵六', department: '后端组', aliases: '' },
  { githubId: 'sunqi', realName: '孙七', department: '后端组', aliases: '' },
  { githubId: 'chenxia', realName: '陈霞', department: '前端组', aliases: '' },
  { githubId: 'zhoujie', realName: '周杰', department: '前端组', aliases: '' },
  { githubId: 'wumei', realName: '吴梅', department: '前端组', aliases: '' },
  { githubId: 'zhenghao', realName: '郑浩', department: '前端组', aliases: '' },
  { githubId: 'huangli', realName: '黄丽', department: '数据组', aliases: '' },
  { githubId: 'xuyang', realName: '徐洋', department: '数据组', aliases: '' },
  { githubId: 'linfang', realName: '林芳', department: '数据组', aliases: '' },
  { githubId: 'heping', realName: '何平', department: '数据组', aliases: '' },
  { githubId: 'guowei', realName: '郭伟', department: '产品组', aliases: '' },
  { githubId: 'mayun', realName: '马芸', department: '产品组', aliases: '' },
  { githubId: 'liuqiang', realName: '刘强', department: '产品组', aliases: '' },
  { githubId: 'gaojie', realName: '高洁', department: '产品组', aliases: '' },
  { githubId: 'tianyu', realName: '田宇', department: '后端组', aliases: '' },
  { githubId: 'xiejing', realName: '谢静', department: '前端组', aliases: '' },
  { githubId: 'dengchao', realName: '邓超', department: '数据组', aliases: '' },
];

// Create worksheet from data
const headers = ['GitHub ID', 'Real Name', 'Department', 'Alias'];
const rows = [headers, ...members.map(m => [m.githubId, m.realName, m.department, m.aliases])];

const ws = XLSX.utils.aoa_to_sheet(rows);

// Set column widths for readability
ws['!cols'] = [
  { wch: 16 }, // GitHub ID
  { wch: 12 }, // Real Name
  { wch: 12 }, // Department
  { wch: 20 }, // Alias(es)
];

// Create workbook
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, ws, 'Members');

// Write file
XLSX.writeFile(wb, 'sample.xlsx');

console.log('✅ sample.xlsx generated successfully!');
console.log(`   ${members.length} members across ${new Set(members.map(m => m.department)).size} departments`);
console.log('   Edit this script with your real team data and re-run to regenerate.');
