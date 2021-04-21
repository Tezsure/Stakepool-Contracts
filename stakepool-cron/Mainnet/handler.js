require('dotenv').config();

const { TezosToolkit } = require('@taquito/taquito');
const { InMemorySigner } = require('@taquito/signer');
const {
    MAINNET_SECRET_KEY,
    MAINNET_CONTRACT_ADDRESS,
    MAINNET_HARBINGER_CONTRACT_ADDRESS,
    MAINNET_RPC_URL,
    TIMER,
} = process.env;

const pingContractMainnet = async () => {
    try {
        console.log('----- Ping contract start -----', MAINNET_SECRET_KEY);
        const rpc = MAINNET_RPC_URL;
        const Tezos = new TezosToolkit(rpc);
        const signer = new InMemorySigner(MAINNET_SECRET_KEY);
        // eslint-disable-next-line no-restricted-properties
        Tezos.setProvider({ signer });
        const contract = await Tezos.contract.at(MAINNET_CONTRACT_ADDRESS);
        const operation = await contract.methods
            .fetchPriceAndUpdateCycle(
                'XTZ-USD',
                MAINNET_HARBINGER_CONTRACT_ADDRESS,
                MAINNET_CONTRACT_ADDRESS
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

pingContractMainnet();
