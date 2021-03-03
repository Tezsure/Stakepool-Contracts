const Axios = require('axios');
const Tezos = require('@taquito/taquito');
const InMemorySigner  = require('@taquito/signer');
const rpc = 'https://testnet.tezster.tech';
const tezos = new Tezos.TezosToolkit(rpc);
var cycle=0;
var errorFlag=false;

const pingContractForCycleAndPriceChange = async () => {
  try {
    const signer = await InMemorySigner.InMemorySigner.fromSecretKey("edskS6DouFfVMwL6YVcHRuJizsPWo8t91h1SR5ZUuRazXDRGVV4eyY7nffoNTXKzP61gqXtPKEPbvZWWkMRga12TKaM7GiMPJi");
    tezos.setProvider({signer});
    tezos.contract.at("KT1LSLUHe9U4MqDuyrMhWThCWu7P6g61vs5k")
        .then(contract => {
            return contract.methods.winningsTransfer("XTZ-USD","KT1LWDzd6mFhjjnb65a1PjHDNZtFKBieTQKH","KT1LSLUHe9U4MqDuyrMhWThCWu7P6g61vs5k").send()
        })
        .then(op => {
            console.log(op.hash);
            return op.confirmation()
        })
        .then(hash => {
            console.log(hash);

        })
        .catch(err => {
            console.log(err);
            console.log(`Setting timeout to error`);
            setTimeout(() => {
              getCycle();
            },60000)
        })
      }catch (err) {
        console.log(err);
        console.log(`Setting timeout to error`);
        setTimeout(() => {
          getCycle();
        },60000)
      }
}

const getCycle = async () => {
  try{
  console.log('----- Fetching initial cycle data -----');
  //let cycleApiResponse = await this._endPointReader.fetchDataPoint(this._tzpoint+this.cycle.toString());
  let cycleApiResponse = await Axios.get(
    "https://api.delphi.tzstats.com/explorer/cycle/"+cycle.toString()
  );
  let cycleEndTime=new Date(cycleApiResponse.data.end_time);
  cycleEndTime.setSeconds(cycleEndTime.getSeconds() + (4*cycleApiResponse.data.solvetime_min));
  let current= new Date();
  if(cycleEndTime.valueOf()<=current.valueOf()||cycleApiResponse.data.is_complete || !cycleApiResponse.data.is_active){
    console.log('----- Updating latest cycle data -----');
    cycleApiResponse=await Axios.get(
      "https://api.delphi.tzstats.com/explorer/cycle/head"
    );
    cycle=cycleApiResponse.data.cycle;
    cycleEndTime=new Date(cycleApiResponse.data.end_time);
    cycleEndTime.setSeconds(cycleEndTime.getSeconds() + (4*cycleApiResponse.data.solvetime_min))
    pingContractForCycleAndPriceChange();
    }else{
      console.log(`The current cycle ${cycle} is still ongoing`);
      }
      setTimeout(() => {
        getCycle();
      },cycleEndTime.valueOf()-current.valueOf())
    }catch (err) {
      console.log(err);
      console.log(`Setting timeout to error`);
      setTimeout(() => {
        getCycle();
      },60000)
    }
}

getCycle();
