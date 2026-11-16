require('dotenv').config();
const express = require('express');
const path = require('path');
const multer = require('multer');
const fs = require('fs');
const crypto = require('crypto');

const app = express();

const {spawn } = require('child_process');

const PYTHON = path.join(__dirname, '.venv', 'bin', 'python');
const PORT = 3013;


//standard ejs middleware
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.json());
app.use(express.urlencoded({extended:true}));
app.use(express.static(path.join(__dirname, 'public')));

//run python scripts 
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

//allow .obj/.csv/.txt uploads
const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 50*1024*1024, files: 1}
});


//run python scripts via jobs 
const jobs = new Map();
function createJob(type) {
    const id = crypto.randomUUID();
    const dir = path.join('data', id);

    fs.mkdirSync(dir, {recursive:true});
    //type: simulation, reconstruction
    //statuses: queued, running, completed, failed
    //stage(simulation): starting simulation, voxelization, generating orientation, simulating dipping, creating dip dataset
    //stage(reconstruction): starting reconstruction, resampling, inverse optimization, clamping, construcing object, building output file
    const job = {
        id, 
        type, 
        status: 'queued', 
        progress:0, 
        stage: 'preprocessing', 
        logs:[], 
        outout:{}}
    jobs.set(id, job);
    return job;

}

function updateJob(job, changes){
    Object.assign(job, changes);
    const payload = JSON.stringify({
        status:job.status, 
        progress: job.progress, 
        stage: job.stage,
        logs: job.logs.slice(-20),
        outputs: job.outputs
    });

}


app.get('/', (req, res) => {
    res.render('home');
});

app.get('/howitworks', (req, res) => {
    res.render('howitworks');
});
app.get('/diy', (req, res) => {
    res.render('diy');
});
app.get('/references', (req, res) => {
    res.render('references');
});


//run scripts

app.post('/simulate', upload.single('obj'), (req, res)=>{
    //collect user inputs
    const shape = req.body.shape;
    const dips = Number(req.body.dips);
    const noise = Number(req.body.noise);
    const job = createJob('simulation');

    //if .obj file is uploaded, use that as shape instead
    if (req.file) {
        const inputPath = path.join('data', 'input.obj');
        fs.writeFileSync(inputPath, req.file.buffer);
        shape = inputPath;
    }

    updateJob(job, {
        status: 'running',
        progress: 0, 
        stage: 'starting simulation'
    });

    //try running the simulator.py asynchrosly
    setImmediate(async () => {
        try{
            await runPython('p1_dip_simulator.py',
                [shape, String(dips), String(noise)],
                'data',
                message => {
                    jobs.logs.push(message);
                    updateJobs(job,  {
                        stage: 'simulating dipping',
                        progress: 50
                        }
                    );
                } 
            );
            const csvPath = path.join('data', 'dip_data.csv')
        
        updateJobs(job,  {
            status: 'completed',
            progress: 100,
            stage: 'dip dataset created',
            outputs: {
            csv: `/data/dip_data.csv`
            }
        });
    } catch (error) {
        jobs.logs.push(error.message);
        updateJob(job, {status: 'failed', stage:'simulation failed'});

    }
    });

});


app.post('/reconstruct', upload.single('csv'), (req, res)=>{
    //collect user inputs

    const job = createJob('reconstruction');

    //if .obj file is uploaded, use that as shape instead
    if (req.file) {
        const inputPath = path.join('data', 'dip_data.csv');
        fs.writeFileSync(inputPath, req.file.buffer);
    }

    updateJob(job, {
        status: 'running',
        stage: 'starting reconstruction'
    });

    //try running the simulator.py asynchrosly
    setImmediate(async () => {
        try{
            await runPython('p2_dip_simulator.py',
                ['dip_data.csv'],
                'data',
                message => {
                    jobs.logs.push(message);
                    updateJobs(job,  {
                        stage: 'reconstructing',
                        progress: 50
                        }
                    );
                } 
            );
            const result = path.join('data', 'dip_reconstruction.obj')
        
        updateJobs(job,  {
            status: 'completed',
            progress: 100,
            stage: 'reconstruction created',
            outputs: {
            csv: `/data/dip_reconstruction.obj`
            }
        });
    } catch (error) {
        jobs.logs.push(error.message);
        updateJob(job, {status: 'failed', stage:'reconstruction failed'});

    }
    });

});

//get 
//error handler
app.use((err, req, res, next)=>{
    console.error(err);
    req.status(err.status || 500).json({
        error:err.status && err.status < 500 ? err.message : "Uh oh."
    });

});


app.listen(PORT, '127.0.0.1', () => {console.log(`http://localhost:${PORT}/`);});

