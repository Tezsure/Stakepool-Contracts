'use strict';
require('dotenv').config();

const Tezos = require('@taquito/taquito');
const InMemorySigner = require('@taquito/signer');
const rpc = process.env.TESTNET_RPC_URL;
const tezos = new Tezos.TezosToolkit(rpc);

const pingContract = async () => {
    console.log('----- Ping contract start -----');
    const {
        TESTNET_SECRET_KEY,
        TESTNET_CONTRACT_ADDRESS,
        TESTNET_HARBINGER_CONTRACT_ADDRESS,
    } = process.env;

    const signer = await InMemorySigner.InMemorySigner.fromSecretKey(
        TESTNET_SECRET_KEY
    );
    tezos.setProvider({
        signer,
    });

    tezos.contract
        .at(TESTNET_CONTRACT_ADDRESS)
        .then((contract) => {
            return contract.methods
                .fetchPriceAndUpdateCycle(
                    'XTZ-USD',
                    TESTNET_HARBINGER_CONTRACT_ADDRESS,
                    TESTNET_CONTRACT_ADDRESS
                )
                .send();
        })
        .then((op) => {
            console.log('------------- Operation -----------------');
            console.log(op);
            return op.confirmation();
        })
        .then((hash) => {
            console.log('------------- Hash -----------------');
            console.log(hash);
        })
        .catch((err) => {
            console.log('------------- Error -----------------');
            console.log(err.message);
        });
};

exports.pingContract = pingContract;
