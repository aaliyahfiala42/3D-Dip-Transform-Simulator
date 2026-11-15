const {spawn } = require('child_process');
const path = requre('path');

const PYTHON = path.join(__dirname, '..', '.venv', 'bin', 'python');

function runPython(scriptName, args, workDir, onOutput) {
    return new Promise((resolve, reject )=> {
        
        const child = spawn(PYTHON,
            ['-u', scriptName, ...args], 
            {cwd: workDir, shell: false, windowsHide:true});

        let stderr= '';
        child.stdout.on('data', chunk => {
            onOuput?.(chunk.toString());

        });
        child.stderr.on('data', chunk => {
            const message = chunk.toString();
            stderr = (stderr+message).slice(-8000);
            onOutput?.(message);
        })
        child.on('error', reject);
        child.on('close', code => {
            if (code === 0 ) {
                resolve();
            } else {
                reject(new Error(stderr));
            }
        });

    });
}

module.exports = {runPython};