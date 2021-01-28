const Axios = require('axios');
const Tezos = require('@taquito/taquito');
const InMemorySigner  = require('@taquito/signer');
const rpc = 'https://testnet.tezster.tech';
const tezos = new Tezos.TezosToolkit(rpc);
var cycle=0;
var errorFlag=false;
const contractAddress = {"tezos":"KT1AQd6KeoPyFJdY4baRyR6zCkGZV2r35K1u", "ethereum":"", "bitcoin":""};

const sendPriceToContract = async (id,price) => {
  try {
    const signer = await InMemorySigner.InMemorySigner.fromSecretKey(process.env.Privatekey);
    tezos.setProvider({signer});
    tezos.contract.at(contractAddress.id)
        .then(contract => {
            return contract.methods.winningsTransfer(price).send()
        })
        .then(op => {
            console.log(op.hash);
            return op.confirmation(2)
        })
        .then(hash => {
            console.log(hash);

        })
        .catch(err => {
            console.log(err);
            console.log(`Setting timeout to error`);
            setTimeout(() => {
                getPrice();
            },60000)
        })
      }catch (err) {
        console.log(err);
        console.log(`Setting timeout to error`);
        setTimeout(() => {
            getPrice();
        },60000)
      }
}

const getPrice = async () => {
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
    Axios.get("https://api.coingecko.com/api/v3/simple/price?ids=tezos%2Cethereum%2Cbitcoin&vs_currencies=usd&include_market_cap=false&include_24hr_vol=false&include_24hr_change=false&include_last_updated_at=true")
        .then(res => {
            for(var priceId in res.data){
              console.log("Data received for "+priceId);
              console.log(res.data.priceId);
              let priceToBeSent = res.data.priceId.usd * 100;
              priceToBeSent = Math.floor(priceToBeSent);
              console.log(priceToBeSent);
              sendPriceToContract(priceId,priceToBeSent);
            }
        })
        .catch(err => {
            console.log(err);
            console.log(`Setting timeout to error`);
            setTimeout(() => {
                getPrice();
            },60000)
        })
    }else{
      console.log(`The current cycle ${cycle} is still ongoing`);
      }
      setTimeout(() => {
          getPrice();
      },cycleEndTime.valueOf()-current.valueOf())
    }catch (err) {
      console.log(err);
      console.log(`Setting timeout to error`);
      setTimeout(() => {
          getPrice();
      },60000)
    }
}

getPrice();
