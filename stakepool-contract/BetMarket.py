#Using maps.Allows the taker to match with the wager whose wager was set first
import smartpy as sp

class StakingMarket(sp.Contract):
    """Initializing the map wager(unmatched wager pool),set inside a map cWager(Matched wager pool),currentPrice(Current price of BTC wrt USD),rate(Staking return percentage in basis points), Baddress(Baking Contract Address),,batchcount(counter that tracks the baker transaction batch),returnCount(Counter that tracks the baker transaction batch that has been completed),wagerCount(Counter that tracks the number of wagers set),admin(address of the contract deployer),detMap(Contains the full details of all the wagers participating in the process)"""
    def __init__(self,admin):
        self.init(rate=sp.nat(144),collateral=sp.mutez(0), withdrawcycle=sp.int(0),admin=sp.set([admin]),rangeEnd=sp.int(1000),rangestep=sp.int(250),interestPool=sp.mutez(0),
        cycleDet=sp.map(tkey=sp.TInt,tvalue=sp.TRecord(cPrice=sp.TInt,cAmount=sp.TMutez, betDet=sp.TMap(sp.TPair(sp.TInt,sp.TInt),sp.TRecord(amt=sp.TMutez,winnings=sp.TMutez,det=sp.TList(sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))))) )

    @sp.entry_point
    def default(self):
        sp.verify(sp.amount >= sp.mutez(0))

    # Admin-only. Give admin rights to an address.
    @sp.entry_point
    def addAdmin(self,access):
        sp.verify(self.data.admin.contains(sp.sender),message="Only existing admins can provide admin rights to other address")
        self.data.admin.add(access)

    # Admin-only. Give admin rights to an address.
    @sp.entry_point
    def removeAdmin(self):
        sp.verify(self.data.admin.contains(sp.sender),message="You are not an admin")
        self.data.admin.remove(sp.sender)

    # Admin-only.Set the range for the strike prices that users can bet on
    @sp.entry_point
    def setBetRange(self,params):
        sp.verify(self.data.admin.contains(sp.sender),message="You are not authoritized to set the range for the available Bet prices")
        self.data.rangeEnd=params.BetPercentEnd
        self.data.rangestep=params.BetPercentIncrementor

    # Admin-only. Delegate the contract's balance.
    @sp.entry_point
    def delegate(self, baker):
        sp.verify(self.data.admin.contains(sp.sender),message="Only admin can delegate contract balance")
        sp.verify(sp.amount == sp.mutez(0))
        sp.set_delegate(baker)

    # Admin-only. Provide tez as collateral for interest to be paid.
    @sp.entry_point
    def collateralize(self):
        sp.verify(self.data.admin.contains(sp.sender),message="Only admin can provide a collateral")
        self.data.collateral += sp.amount

    # Admin-only. Withdraw collateral.
    @sp.entry_point
    def uncollateralize(self, amount):
        sp.verify(self.data.admin.contains(sp.sender),message="Only admin can withdraw a collateral")
        sp.verify(self.data.collateral >= amount,message="Insufficient collateral funds to meet your withdraw request")
        self.data.collateral -= amount
        sp.send(sp.sender, amount)

    # Admin-only. Set the current offer: interest rate (in basis points),fee rate(in basis points).
    @sp.entry_point
    def changeOffer(self, rate):
        sp.verify(self.data.admin.contains(sp.sender),message="Only admins can change the current offer")
        self.data.rate = rate

    @sp.entry_point
    def setWager(self,spercent):
        sp.verify(self.data.withdrawcycle!=0,message="Please wait for the new cycle to initiate being matching with a wager")
        sp.verify(sp.amount>=sp.tez(1),message="Please send in the correct amount to be staked for this wager")
        sp.verify(self.data.cycleDet[self.data.withdrawcycle].betDet.contains(spercent),message="Please enter the correct Strike Percentage Range")
        #details passed by the wager is added to detMap and unconfirmed wager pool.And the wagerCount is incremented
        self.data.cycleDet[self.data.withdrawcycle].betDet[spercent].det.push(sp.record(bettor=sp.sender,invest=sp.amount))
        self.data.cycleDet[self.data.withdrawcycle].betDet[spercent].amt+=sp.amount
        self.data.cycleDet[self.data.withdrawcycle].cAmount+=sp.amount

    @sp.entry_point
    def winningsTransfer(self,currentPrice):
        sp.verify(self.data.admin.contains(sp.sender),message="You are not authorised to use this function")
        cycleref = sp.local("cycleref", sp.int(0))
        interest=sp.local("interest",sp.mutez(0))
        spnew=sp.local("spnew",sp.int(0))
        cycleref.value=self.data.withdrawcycle-5
        self.data.withdrawcycle+=1
        self.data.cycleDet[self.data.withdrawcycle]=sp.record(cPrice=currentPrice,cAmount=sp.mutez(0),betDet=sp.map(tkey=sp.TPair(sp.TInt,sp.TInt), tvalue=sp.TRecord(amt=sp.TMutez,winnings=sp.TMutez,det=sp.TList(sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))))
        sp.if cycleref.value>0:
            sp.if self.data.cycleDet[cycleref.value].cAmount!=sp.mutez(0):
                interest.value=sp.split_tokens(self.data.cycleDet[cycleref.value].cAmount,self.data.rate,sp.nat(10000))
                sp.verify(sp.balance-self.data.cycleDet[cycleref.value].cAmount>interest.value+self.data.interestPool,message="Insufficient Contract Balance to transfer the winnings of this baking cycle.")
                #Initializing local variables wRate,lRate,wInterest,lInterest to hold the values of the winning and losing rate and subsequent interest they have won
                sp.for x in self.data.cycleDet[cycleref.value].betDet.keys():
                    sp.if sp.fst(x)==sp.snd(x):
                        sp.if sp.fst(x)<0:
                            sp.if currentPrice<self.data.cycleDet[cycleref.value].cPrice-sp.fst(sp.ediv(sp.fst(x)*self.data.cycleDet[cycleref.value].cPrice,sp.int(10000)).open_some()):
                                sp.if self.data.cycleDet[cycleref.value].cAmount!=self.data.cycleDet[cycleref.value].betDet[x].amt:
                                    sp.if self.data.cycleDet[cycleref.value].betDet[x].amt!=sp.mutez(0):
                                        self.data.collateral+=sp.split_tokens(interest.value,sp.nat(200),sp.nat(10000))
                                        interest.value-=sp.split_tokens(interest.value,sp.nat(200),sp.nat(10000))
                                        self.data.cycleDet[cycleref.value].betDet[x].winnings=interest.value
                                        sp.for y in self.data.cycleDet[cycleref.value].betDet[x].det:
                                            sp.send(y.bettor,y.invest+sp.split_tokens(interest.value+self.data.interestPool,sp.fst(sp.ediv(y.invest,sp.mutez(1)).open_some()),sp.fst(sp.ediv(self.data.cycleDet[cycleref.value].betDet[x].amt,sp.mutez(1)).open_some())))
                                        self.data.interestPool=sp.mutez(0)
                                    sp.else:
                                        self.data.collateral+=sp.split_tokens(interest.value,sp.nat(200),sp.nat(10000))
                                        self.data.interestPool=sp.split_tokens(interest.value,sp.nat(9800),sp.nat(10000))
                                sp.else:
                                    self.data.cycleDet[cycleref.value].betDet[x].winnings=interest.value
                                    sp.for y in self.data.cycleDet[cycleref.value].betDet[x].det:
                                        sp.send(y.bettor,y.invest+sp.split_tokens(interest.value+self.data.interestPool,sp.fst(sp.ediv(y.invest,sp.mutez(1)).open_some()),sp.fst(sp.ediv(self.data.cycleDet[cycleref.value].betDet[x].amt,sp.mutez(1)).open_some())))
                                    self.data.interestPool=sp.mutez(0)
                            sp.else:
                                sp.if self.data.cycleDet[cycleref.value].betDet[x].amt!=sp.mutez(0):
                                    sp.for y in self.data.cycleDet[cycleref.value].betDet[x].det:
                                        sp.send(y.bettor,y.invest)
                        sp.else:
                            sp.if currentPrice>=self.data.cycleDet[cycleref.value].cPrice-sp.fst(sp.ediv(sp.fst(x)*self.data.cycleDet[cycleref.value].cPrice,sp.int(10000)).open_some()):
                                sp.if self.data.cycleDet[cycleref.value].cAmount!=self.data.cycleDet[cycleref.value].betDet[x].amt:
                                    sp.if self.data.cycleDet[cycleref.value].betDet[x].amt!=sp.mutez(0):
                                        self.data.collateral+=sp.split_tokens(interest.value,sp.nat(200),sp.nat(10000))
                                        interest.value-=sp.split_tokens(interest.value,sp.nat(200),sp.nat(10000))
                                        self.data.cycleDet[cycleref.value].betDet[x].winnings=interest.value
                                        sp.for y in self.data.cycleDet[cycleref.value].betDet[x].det:
                                            sp.send(y.bettor,y.invest+sp.split_tokens(interest.value+self.data.interestPool,sp.fst(sp.ediv(y.invest,sp.mutez(1)).open_some()),sp.fst(sp.ediv(self.data.cycleDet[cycleref.value].betDet[x].amt,sp.mutez(1)).open_some())))
                                        self.data.interestPool=sp.mutez(0)
                                    sp.else:
                                        self.data.collateral+=sp.split_tokens(interest.value,sp.nat(200),sp.nat(10000))
                                        self.data.interestPool=sp.split_tokens(interest.value,sp.nat(9800),sp.nat(10000))
                                sp.else:
                                    self.data.cycleDet[cycleref.value].betDet[x].winnings=interest.value
                                    sp.for y in self.data.cycleDet[cycleref.value].betDet[x].det:
                                        sp.send(y.bettor,y.invest+sp.split_tokens(interest.value+self.data.interestPool,sp.fst(sp.ediv(y.invest,sp.mutez(1)).open_some()),sp.fst(sp.ediv(self.data.cycleDet[cycleref.value].betDet[x].amt,sp.mutez(1)).open_some())))
                                    self.data.interestPool=sp.mutez(0)
                            sp.else:
                                sp.if self.data.cycleDet[cycleref.value].betDet[x].amt!=sp.mutez(0):
                                    sp.for y in self.data.cycleDet[cycleref.value].betDet[x].det:
                                        sp.send(y.bettor,y.invest)
                    sp.else:
                        sp.if (currentPrice>=self.data.cycleDet[cycleref.value].cPrice-sp.fst(sp.ediv(sp.fst(x)*self.data.cycleDet[cycleref.value].cPrice,sp.int(10000)).open_some()))&(currentPrice<self.data.cycleDet[cycleref.value].cPrice-sp.fst(sp.ediv(sp.snd(x)*self.data.cycleDet[cycleref.value].cPrice,sp.int(10000)).open_some())):
                            sp.if self.data.cycleDet[cycleref.value].cAmount!=self.data.cycleDet[cycleref.value].betDet[x].amt:
                                sp.if self.data.cycleDet[cycleref.value].betDet[x].amt!=sp.mutez(0):
                                    self.data.collateral+=sp.split_tokens(interest.value,sp.nat(200),sp.nat(10000))
                                    interest.value-=sp.split_tokens(interest.value,sp.nat(200),sp.nat(10000))
                                    self.data.cycleDet[cycleref.value].betDet[x].winnings=interest.value
                                    sp.for y in self.data.cycleDet[cycleref.value].betDet[x].det:
                                        sp.send(y.bettor,y.invest+sp.split_tokens(interest.value+self.data.interestPool,sp.fst(sp.ediv(y.invest,sp.mutez(1)).open_some()),sp.fst(sp.ediv(self.data.cycleDet[cycleref.value].betDet[x].amt,sp.mutez(1)).open_some())))
                                    self.data.interestPool=sp.mutez(0)
                                sp.else:
                                    self.data.collateral+=sp.split_tokens(interest.value,sp.nat(200),sp.nat(10000))
                                    self.data.interestPool=sp.split_tokens(interest.value,sp.nat(9800),sp.nat(10000))
                            sp.else:
                                self.data.cycleDet[cycleref.value].betDet[x].winnings=interest.value
                                sp.for y in self.data.cycleDet[cycleref.value].betDet[x].det:
                                    sp.send(y.bettor,y.invest+sp.split_tokens(interest.value+self.data.interestPool,sp.fst(sp.ediv(y.invest,sp.mutez(1)).open_some()),sp.fst(sp.ediv(self.data.cycleDet[cycleref.value].betDet[x].amt,sp.mutez(1)).open_some())))
                                self.data.interestPool=sp.mutez(0)
                        sp.else:
                            sp.if self.data.cycleDet[cycleref.value].betDet[x].amt!=sp.mutez(0):
                                sp.for y in self.data.cycleDet[cycleref.value].betDet[x].det:
                                    sp.send(y.bettor,y.invest)

                    sp.if spnew.value<=self.data.rangeEnd:
                        sp.if spnew.value+self.data.rangestep<=self.data.rangeEnd:
                            self.data.cycleDet[self.data.withdrawcycle].betDet[(spnew.value,spnew.value+self.data.rangestep)]=sp.record(amt=sp.mutez(0),winnings=sp.mutez(0),det=sp.list(t=sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))
                            self.data.cycleDet[self.data.withdrawcycle].betDet[(sp.int(-1)*(spnew.value+self.data.rangestep),sp.int(-1)*spnew.value)]=sp.record(amt=sp.mutez(0),winnings=sp.mutez(0),det=sp.list(t=sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))
                        sp.else:
                            self.data.cycleDet[self.data.withdrawcycle].betDet[(spnew.value,spnew.value)]=sp.record(amt=sp.mutez(0),winnings=sp.mutez(0),det=sp.list(t=sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))
                            self.data.cycleDet[self.data.withdrawcycle].betDet[(sp.int(-1)*spnew.value,sp.int(-1)*spnew.value)]=sp.record(amt=sp.mutez(0),winnings=sp.mutez(0),det=sp.list(t=sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))
                        spnew.value+=self.data.rangestep
            sp.if cycleref.value>5:
                del self.data.cycleDet[cycleref.value-5]
        sp.while spnew.value<=self.data.rangeEnd:
            sp.if spnew.value+self.data.rangestep<=self.data.rangeEnd:
                self.data.cycleDet[self.data.withdrawcycle].betDet[(spnew.value,spnew.value+self.data.rangestep)]=sp.record(amt=sp.mutez(0),winnings=sp.mutez(0),det=sp.list(t=sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))
                self.data.cycleDet[self.data.withdrawcycle].betDet[(sp.int(-1)*(spnew.value+self.data.rangestep),sp.int(-1)*spnew.value)]=sp.record(amt=sp.mutez(0),winnings=sp.mutez(0),det=sp.list(t=sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))
            sp.else:
                self.data.cycleDet[self.data.withdrawcycle].betDet[(spnew.value,spnew.value)]=sp.record(amt=sp.mutez(0),winnings=sp.mutez(0),det=sp.list(t=sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))
                self.data.cycleDet[self.data.withdrawcycle].betDet[(sp.int(-1)*spnew.value,sp.int(-1)*spnew.value)]=sp.record(amt=sp.mutez(0),winnings=sp.mutez(0),det=sp.list(t=sp.TRecord(bettor=sp.TAddress,invest=sp.TMutez)))
            spnew.value+=self.data.rangestep




@sp.add_test(name = "Test Market")
def test():
    scenario = sp.test_scenario()
    scenario.h1("Market Demo")
    wagerA = sp.test_account("wagerA")
    wagerB = sp.test_account("wagerB")
    wagerC = sp.test_account("wagerC")
    takerA = sp.test_account("takerA")
    takerB = sp.test_account("takerB")
    admin = sp.test_account("admin")
    c1 = StakingMarket(sp.address("tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795"))
    scenario += c1
    scenario += c1.default().run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.addAdmin(sp.address("tz1N2SiwSoTEs8RXKxirYBVN95yoVJuQhPJ2")).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.delegate(sp.some(sp.key_hash("tz1YB12JHVHw9GbN66wyfakGYgdTBvokmXQk"))).run(sender = sp.address("tz1N2SiwSoTEs8RXKxirYBVN95yoVJuQhPJ2"))
    scenario += c1.delegate(sp.none).run(sender =sp.address("tz1N2SiwSoTEs8RXKxirYBVN95yoVJuQhPJ2"))
    scenario += c1.winningsTransfer(200).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    #scenario += c1.setWager(250).run(sender = wagerA, amount = sp.tez(20))
    #scenario += c1.matchWager(250).run(sender = takerA, amount = sp.tez(20))
"""
    scenario += c1.winningsTransfer(150).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.winningsTransfer(200).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.winningsTransfer(200).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.winningsTransfer(200).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.winningsTransfer(200).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.winningsTransfer(200).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.winningsTransfer(200).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.winningsTransfer(200).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
    scenario += c1.winningsTransfer(200).run(sender=sp.address('tz1PQ7zecVpTKHvPvjaicGRSYrweBEJ5J795'))
"""
