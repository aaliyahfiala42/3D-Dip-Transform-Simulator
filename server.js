const express = require('express');
const path = require('path');
const multer = require('multer');
const fs = require('fs');
const crypto = require('crypto');

const app = express();

const {spawn } = require('child_process');

const PYTHON = path.join(__dirname, '.venv', 
    process.platform === 'win32' ? 'Scripts/python.exe'
    : 'bin/python');
const SCRIPTS = path.join(__dirname, 'scripts');
const DATA = path.join(__dirname, 'data');

const PORT = 3013;


//standard ejs middleware
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.json());
app.use(express.urlencoded({extended:true}));
app.use(express.static(path.join(__dirname, 'public')));



fs.mkdirSync(DATA, {recursive:true});
//allow .obj/.csv/.txt uploads
const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 50*1024*1024, files: 1}
});


//run python scripts via jobs 
const jobs = new Map();
function createJob(type) {
    const id = crypto.randomUUID();

    const dir = path.join(DATA, id);
    fs.mkdirSync(dir, {recursive:true});

    //type: simulation, reconstruction
    //statuses: queued, running, completed, failed
    //stage(simulation): starting simulation, voxelization, generating orientation, simulating dipping, creating dip dataset, simulator complete
    //stage(reconstruction): starting reconstruction, resampling, inverse optimization, clamping, construcing object, building output file
    const job = {
        id, dir,
        type, 
        status: 'running', 
        output: '', 
        outputs:{}}
    jobs.set(id, job);
    return job;

}

//run python scripts (dip_simualtor.py or dip_reconstruction.py), collect output, get progress status, resolve on finish
function runPython(script, args, job) {
    return new Promise((resolve, reject )=> {
        
        const child = spawn(PYTHON,
            ['-u', path.join(SCRIPTS, script), ...args], 
            {cwd: job.dir, 
                env: {
                    ...process.env, PYTHONIOENCODING: 'utf-8'
                }
            });


        child.stdout.on('data', chunk => {
            job.output += chunk.toString();
            job.output = job.output.slice(-100000);

        });

        child.stderr.on('data', chunk => {
            job.output += chunk.toString();
            job.output = job.output.slice(-100000);
        });

        child.on('error', reject);
        child.on('close', code => {
            if(code === 0) { resolve() }
            else {reject(new Error(code))};
        });

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
    const job = createJob('simulation');

    //collect user inputs
    let shape = req.body.shape;
    const dips = String(req.body.dips);
    const noise = String(req.body.noise);
 

    //if .obj file is uploaded, use that as shape instead
    if (req.file) {
        shape = path.join(job.dir, 'input.obj');
        fs.writeFileSync(shape, req.file.buffer);
    }
    
    res.json({jobId: job.id});

    //try running the simulator.py asynchrosly
    (async () => {
        try{
            await runPython('p1_dip_simulator.py',
                [shape, dips, noise],
                job);
            job.outputs = {obj: 'input.obj', csv: 'dip_data.csv'};
            job.status = 'completed';

    } catch (error) {
        job.status= 'failed';
        job.output += error.message;

    }
    })();

});


app.post('/reconstruct', upload.single('csv'), (req, res)=>{
    //collect user inputs

    const job = createJob('reconstruction');
        
    const input = path.join(job.dir, 'dip_data.csv');
    

    //if .obj file is uploaded, use that as shape instead
    if (req.file) {
        fs.writeFileSync(input, req.file.buffer);
    } else {
        const previous = jobs.get(req.body.sourceJob);
        fs.copyFileSync(path.join(previous.dir, 'dip_data.csv'), input);
    }

    res.json({jobId: job.id});

    //try running the reconstructor.py asynchrosly
    (async () => {
        try{
            await runPython('p2_dip_reconstructor.py',
                ['dip_data.csv'],
                job

            );
            const objPath = path.join(job.dir, 'dip_reconstruction.obj');
            
            job.status= 'completed';
            job.outputs = {obj: 'dip_reconstruction.obj' }

    } catch (error) {
        job.status = 'failed';
        job.output += error.message;

    }
    })();

});

//get current job info
app.get('/job/:id', (req, res) => {
    const job = jobs.get(req.params.id);
    if(!job) return res.sendStatus(400);

    res.json({
        status:job.status,
        output:job.output,
        outputs:job.outputs
    });
});
// make script outputs downloadable
app.get('/data/:id/:name', (req, res) => {
    const job = jobs.get(req.params.id);
    if(!job) return res.sendStatus(404);

    const filename = req.params.name;
    res.sendFile(path.join(job.dir, filename));
});

//error handler
app.use((err, req, res, next) => {
    console.error(err);
    res.status(500).json({ error: err.message });
});

app.listen(PORT, '127.0.0.1', () => {console.log(`http://localhost:${PORT}/`);});

