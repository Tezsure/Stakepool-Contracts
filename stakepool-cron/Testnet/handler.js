require('dotenv').config();

const { TezosToolkit } = require('@taquito/taquito');
const { InMemorySigner } = require('@taquito/signer');
const {
    TESTNET_SECRET_KEY,
    TESTNET_CONTRACT_ADDRESS,
    TESTNET_HARBINGER_CONTRACT_ADDRESS,
    TESTNET_RPC_URL,
    TIMER,
} = process.env;

const pingContractTestnet = async () => {
    try {
        console.log('----- Ping contract start -----', TESTNET_SECRET_KEY);
        const rpc = TESTNET_RPC_URL;
        const Tezos = new TezosToolkit(rpc);
        const signer = new InMemorySigner(TESTNET_SECRET_KEY);
        // eslint-disable-next-line no-restricted-properties
        Tezos.setProvider({ signer });
        const contract = await Tezos.contract.at(TESTNET_CONTRACT_ADDRESS);
        const operation = await contract.methods
            .fetchPriceAndUpdateCycle(
                'XTZ-USD',
                TESTNET_HARBINGER_CONTRACT_ADDRESS,
                TESTNET_CONTRACT_ADDRESS
            )
            .send();
        console.log('----------- operation --------', operation);
        await operation.confirmation(1).then(() => operation.opHash);
        setTimeout(() => {
            pingContractTestnet();
        }, TIMER);
    } catch (error) {
        console.log('----------- Error --------', error);
        console.error(error);
        setTimeout(() => {
            pingContractTestnet();
        }, TIMER);
    }
};

pingContractTestnet();
