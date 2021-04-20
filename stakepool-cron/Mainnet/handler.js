require('dotenv').config();

const Tezos = require('@taquito/taquito');
const InMemorySigner = require('@taquito/signer');
const rpc = 'https://mainnet-tezos.giganode.io';
const tezos = new Tezos.TezosToolkit(rpc);

const pingContractMainnet = async () => {
    console.log('----- Ping contract start -----');
    const {
        MAINNET_SECRET_KEY,
        MAINNET_CONTRACT_ADDRESS,
        MAINNET_HARBINGER_CONTRACT_ADDRESS,
    } = process.env;
    const signer = await InMemorySigner.InMemorySigner.fromSecretKey(
        MAINNET_SECRET_KEY
    );
    tezos.setProvider({ signer });

    tezos.contract
        .at(MAINNET_CONTRACT_ADDRESS)
        .then((contract) => {
            return contract.methods
                .fetchPriceAndUpdateCycle(
                    'XTZ-USD',
                    MAINNET_HARBINGER_CONTRACT_ADDRESS,
                    MAINNET_CONTRACT_ADDRESS
                )
                .send();
        })
        .then((op) => {
            console.log('------------- Operation -----------------');
            console.log(op);
            console.log(op.hash);
            return op.confirmation();
        })
        .then((hash) => {
            console.log('------------- Hash -----------------');
            console.log(hash);
        })
        .catch((err) => {
            console.log('------------- Error -----------------');
            console.log(err);
        });
};

exports.pingContractMainnet = pingContractMainnet;
