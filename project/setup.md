# Set Up

Requirements:
- Python 3.7 or higher
- Typescript
- Bril Repository
- CS6120-Jonathan Repository

## Bril Vector Extension

You will want to set up the Bril Vector Extension interpreter. To do so, look inside
the `typescript-vectorization` subfolder in the current `project` directory. Drag
all 3 files into the `bril/bril-ts` folder inside the `bril` git repository. You will
have to overwrite the `package.json` with the new one I have provided.

Once the three files are moved, you can then run the commands:
```zsh
yarn 
yarn build
yarn unlink
yarn link
```
which should add `brili-vc` to be a command on the command line. Running `brili-vc`
in place of `brili` allows for interpretation of vector instructions.

## Vectorizaiton

All other vectorization source files are in the `CS6120-Jonathan` folder. The common workflow to 
run these files are
```zsh
bril2json < test-you-want-to-run | python3 vectorization-you-want-to-run.py | brili-vc
```

Some vectorization options are:
`naive_vectorization.py` and `opportunistic_lvn_slp.py`.

Tests can be chosne in the folder `vectorization-tests`.

You can also run tests to check that `brili-vc` works as intended. These tests lie in 
`vector-interpreter-tests`.

Vectorization depends on several other primitives, including alias analysis and loop unrolling.
These files are located at `alias_analysis.py` and `loop_unrolling.py`. Tests for these files
are at `alias-analysis-tests` and `unrolling-tests`.