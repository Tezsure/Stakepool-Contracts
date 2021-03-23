import smartpy as sp


class StakingMarket(sp.Contract):
    def __init__(self, admin):
        self.init(rate=sp.nat(144), collateral=sp.mutez(0), currentReferenceRewardCycle=sp.int(0), admin=sp.set([admin]), rangeEnd=sp.int(1000), rangestep=sp.int(250), rewardCarryForwarded=sp.mutez(0),
                  cycleOperations=sp.map(tkey=sp.TInt, tvalue=sp.TRecord(priceAtCurrentCycle=sp.TInt, cAmount=sp.TMutez, rangeDetails=sp.TMap(sp.TPair(sp.TInt, sp.TInt), sp.TRecord(amountInRange=sp.TMutez, totalRewards=sp.TMutez, bettorsDetails=sp.TList(sp.TRecord(bettor=sp.TAddress, betAmount=sp.TMutez)))))))

    def rangeCheck(self, params):
        sp.if sp.fst(params.rangeData) == sp.snd(params.rangeData):
            sp.if sp.fst(params.rangeData) < 0:
                self.checkBelowRangeStatus(params)
            sp.else:
                self.checkAboveRangeStatus(params)
        sp.else:
            self.checkBetweenRangeStatus(params)

    def checkBelowRangeStatus(self, params):
        sp.if params.currentPrice < self.data.cycleOperations[params.currentReferenceWithdrawCycle].priceAtCurrentCycle+sp.fst(sp.ediv(sp.fst(params.rangeData)*self.data.cycleOperations[params.currentReferenceWithdrawCycle].priceAtCurrentCycle, sp.int(10000)).open_some()):
            self.checkWinnerCase(params)
        sp.else:
            self.transferLoserAmount(params)

    def checkAboveRangeStatus(self, params):
        sp.if params.currentPrice >= self.data.cycleOperations[params.currentReferenceWithdrawCycle].priceAtCurrentCycle+sp.fst(sp.ediv(sp.fst(params.rangeData)*self.data.cycleOperations[params.currentReferenceWithdrawCycle].priceAtCurrentCycle, sp.int(10000)).open_some()):
            self.checkWinnerCase(params)
        sp.else:
            self.transferLoserAmount(params)

    def checkBetweenRangeStatus(self, params):
        sp.if (params.currentPrice >= self.data.cycleOperations[params.currentReferenceWithdrawCycle].priceAtCurrentCycle+sp.fst(sp.ediv(sp.fst(params.rangeData)*self.data.cycleOperations[params.currentReferenceWithdrawCycle].priceAtCurrentCycle, sp.int(10000)).open_some())) & (params.currentPrice < self.data.cycleOperations[params.currentReferenceWithdrawCycle].priceAtCurrentCycle+sp.fst(sp.ediv(sp.snd(params.rangeData)*self.data.cycleOperations[params.currentReferenceWithdrawCycle].priceAtCurrentCycle, sp.int(10000)).open_some())):
            self.checkWinnerCase(params)
        sp.else:
            sp.if self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].amountInRange != sp.mutez(0):
                self.transferLoserAmount(params)

    def checkWinnerCase(self, params):
        sp.if self.data.cycleOperations[params.currentReferenceWithdrawCycle].cAmount != self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].amountInRange:
            sp.if self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].amountInRange != sp.mutez(0):
                self.transferWinnerAmount(params)
            sp.else:
                self.carryForwardAmountToNextCycle(params)
        sp.else:
            # The initial investment along with usual baking rewards is being transferred without platform fee since there is no other active bet range
            self.transferAmount(params)

    def transferWinnerAmount(self, params):
        # 2% platform usage fee is automatically added to the collateral for self sustained platform
        self.data.collateral += sp.split_tokens(
            params.rewards, sp.nat(200), sp.nat(10000))
        params.rewards -= sp.split_tokens(params.rewards,
                                          sp.nat(200), sp.nat(10000))
        self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].totalRewards = params.rewards
        sp.for bettorsData in self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].bettorsDetails:
            sp.send(bettorsData.bettor, bettorsData.betAmount+sp.split_tokens(params.rewards+self.data.rewardCarryForwarded, sp.fst(sp.ediv(bettorsData.betAmount, sp.mutez(1)).open_some()),
                                                                              sp.fst(sp.ediv(self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].amountInRange, sp.mutez(1)).open_some())))
        self.data.rewardCarryForwarded = sp.mutez(0)

    def carryForwardAmountToNextCycle(self, params):
        self.data.collateral += sp.split_tokens(
            params.rewards, sp.nat(200), sp.nat(10000))
        self.data.rewardCarryForwarded = sp.split_tokens(
            params.rewards, sp.nat(9800), sp.nat(10000))

    def transferAmount(self, params):
        self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].totalRewards = params.rewards
        sp.for bettorsData in self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].bettorsDetails:
            sp.send(bettorsData.bettor, bettorsData.betAmount+sp.split_tokens(params.rewards+self.data.rewardCarryForwarded, sp.fst(sp.ediv(bettorsData.betAmount, sp.mutez(1)).open_some()),
                                                                              sp.fst(sp.ediv(self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].amountInRange, sp.mutez(1)).open_some())))
        self.data.rewardCarryForwarded = sp.mutez(0)

    def transferLoserAmount(self, params):
        sp.for bettorsData in self.data.cycleOperations[params.currentReferenceWithdrawCycle].rangeDetails[params.rangeData].bettorsDetails:
            sp.send(bettorsData.bettor, bettorsData.betAmount)

    # Sets a structure for new cycle data
    def initialiseNewCycleData(self):
        spnew = sp.local("spnew", sp.int(0))
        sp.while spnew.value <= self.data.rangeEnd:
            sp.if spnew.value+self.data.rangestep <= self.data.rangeEnd:
                self.data.cycleOperations[self.data.currentReferenceRewardCycle].rangeDetails[(spnew.value, spnew.value+self.data.rangestep)] = sp.record(
                    amountInRange=sp.mutez(0), totalRewards=sp.mutez(0), bettorsDetails=sp.list(t=sp.TRecord(bettor=sp.TAddress, betAmount=sp.TMutez)))
                self.data.cycleOperations[self.data.currentReferenceRewardCycle].rangeDetails[(sp.int(-1)*(spnew.value+self.data.rangestep), sp.int(-1)*spnew.value)] = sp.record(
                    amountInRange=sp.mutez(0), totalRewards=sp.mutez(0), bettorsDetails=sp.list(t=sp.TRecord(bettor=sp.TAddress, betAmount=sp.TMutez)))
            # handling extreme ranges initialisation
            sp.else:
                self.data.cycleOperations[self.data.currentReferenceRewardCycle].rangeDetails[(spnew.value, spnew.value)] = sp.record(
                    amountInRange=sp.mutez(0), totalRewards=sp.mutez(0), bettorsDetails=sp.list(t=sp.TRecord(bettor=sp.TAddress, betAmount=sp.TMutez)))
                self.data.cycleOperations[self.data.currentReferenceRewardCycle].rangeDetails[(sp.int(-1)*spnew.value, sp.int(-1)*spnew.value)] = sp.record(
                    amountInRange=sp.mutez(0), totalRewards=sp.mutez(0), bettorsDetails=sp.list(t=sp.TRecord(bettor=sp.TAddress, betAmount=sp.TMutez)))
            spnew.value += self.data.rangestep

    # Is used by winningsTransfer entry point to call Harbinger Oracle.

    def fetchPriceFromHarbinger(self, harbingerContractAddress, asset, targetAddress):
        contractParams = sp.contract(sp.TPair(sp.TString, sp.TContract(sp.TPair(sp.TString, sp.TPair(
            sp.TTimestamp, sp.TNat)))), harbingerContractAddress, entry_point="get").open_some()

        callBack = sp.contract(sp.TPair(sp.TString, sp.TPair(
            sp.TTimestamp, sp.TNat)), targetAddress, entry_point="getResponseFromHarbinger").open_some()

        dataToBeSent = sp.pair(asset, callBack)

        sp.transfer(dataToBeSent, sp.mutez(0), contractParams)

    # Mostly for recieving rewards from baker
    @sp.entry_point
    def default(self):
        sp.verify(sp.amount >= sp.mutez(0))
        self.data.collateral += sp.amount

    # Admin-only. Give admin rights to an address.
    @sp.entry_point
    def addAdmin(self, access):
        sp.verify(self.data.admin.contains(
            sp.sender), message="Only existing admins can provide admin rights to other address")
        self.data.admin.add(access)

    # Admin-only. Give admin rights to an address.
    @sp.entry_point
    def removeAdmin(self):
        sp.verify(self.data.admin.contains(sp.sender),
                  message="You are not an admin")
        self.data.admin.remove(sp.sender)

    # Admin-only.Set the range for the strike prices that users can bet on, this is useful when volatility changes and ranges are to be shrinked or expanded.
    @sp.entry_point
    def setBetRange(self, params):
        sp.verify(self.data.admin.contains(
            sp.sender), message="You are not authoritized to set the range for the available Bet prices")
        self.data.rangeEnd = params.BetPercentEnd
        self.data.rangestep = params.BetPercentIncrementor

    # Admin-only. Delegate the contract's balance.
    @sp.entry_point
    def delegate(self, baker):
        sp.verify(self.data.admin.contains(sp.sender),
                  message="Only admin can delegate contract balance")
        sp.verify(sp.amount == sp.mutez(0))
        sp.set_delegate(baker)

    # Admin-only. Provide tez as collateral for rewards to be paid.
    @sp.entry_point
    def collateralize(self):
        sp.verify(self.data.admin.contains(sp.sender),
                  message="Only admin can provide a collateral")
        self.data.collateral += sp.amount

    # Admin-only. Withdraw collateral.
    @sp.entry_point
    def uncollateralize(self, amount):
        sp.verify(self.data.admin.contains(sp.sender),
                  message="Only admin can withdraw a collateral")
        sp.verify(self.data.collateral >= amount,
                  message="Insufficient collateral funds to meet your withdraw request")
        self.data.collateral -= amount
        sp.send(sp.sender, amount)

    # Admin-only. Retrieve token from contract.
    @sp.entry_point
    def retrieveToken(self, amount, address):
        sp.verify(self.data.admin.contains(sp.sender),
                  message="Only admin can retrieve token")
        sp.verify(sp.balance >= amount,
                  message="Insufficient funds to meet your retreive token request")
        sp.send(address, amount)

    # Admin-only. Set the current offer: rewards rate (in basis points).
    @sp.entry_point
    def changeRewardRoi(self, rate):
        sp.verify(self.data.admin.contains(sp.sender),
                  message="Only admins can change the current offer")
        self.data.rate = rate

    # This entry point allows a bettor to place bet in current cycle.
    @sp.entry_point
    def placeBet(self, spercent):
        sp.verify(self.data.currentReferenceRewardCycle != 0,
                  message="Please wait for the new cycle to initiate being matching with a wager")
        sp.verify(sp.amount >= sp.tez(
            1), message="Please send in the correct amount to be staked for this wager")
        sp.verify(self.data.cycleOperations[self.data.currentReferenceRewardCycle].rangeDetails.contains(
            spercent), message="Invalid Range")

        # details passed by the wager is added to detMap and unconfirmed wager pool.And the wagerCount is incremented
        self.data.cycleOperations[self.data.currentReferenceRewardCycle].rangeDetails[spercent].bettorsDetails.push(
            sp.record(bettor=sp.sender, betAmount=sp.amount))
        self.data.cycleOperations[self.data.currentReferenceRewardCycle].rangeDetails[spercent].amountInRange += sp.amount
        self.data.cycleOperations[self.data.currentReferenceRewardCycle].cAmount += sp.amount

    # Initiates the process of rewards transfer at end of every cycle and creates a structure for a new cycle.
    @sp.entry_point
    def winningsTransfer(self, params):
        sp.verify(self.data.admin.contains(sp.sender),
                  message="You are not authorised to use this function")
        self.fetchPriceFromHarbinger(
            params.harbingerContractAddress, params.asset, params.targetAddress)

    # For getting response from harbinger and performing calculations for returning rewards or rewards + stake , depending upon whether bettor wins or loses. This entry point is called from harbinger oracle once we send request.

    @sp.entry_point
    def getResponseFromHarbinger(self, response):
        sp.set_type(response, sp.TPair(
            sp.TString, sp.TPair(sp.TTimestamp, sp.TNat)))

        currentReferenceWithdrawCycle = sp.local(
            "currentReferenceWithdrawCycle", sp.int(0))
        sp.verify(self.data.admin.contains(sp.source),
                  message="You are not authorised to use this function")
        cp = sp.local("cp", sp.int(0))
        #cp = sp.snd(sp.snd(response))
        cp = sp.to_int(
            sp.fst(sp.ediv(sp.snd(sp.snd(response)), sp.nat(10000)).open_some()))
        rewards = sp.local("rewards", sp.mutez(0))
        currentReferenceWithdrawCycle.value = self.data.currentReferenceRewardCycle-7
        self.data.currentReferenceRewardCycle += 1
        self.data.cycleOperations[self.data.currentReferenceRewardCycle] = sp.record(priceAtCurrentCycle=cp, cAmount=sp.mutez(0), rangeDetails=sp.map(tkey=sp.TPair(
            sp.TInt, sp.TInt), tvalue=sp.TRecord(amountInRange=sp.TMutez, totalRewards=sp.TMutez, bettorsDetails=sp.TList(sp.TRecord(bettor=sp.TAddress, betAmount=sp.TMutez)))))

        sp.if currentReferenceWithdrawCycle.value > 0:
            sp.if self.data.cycleOperations[currentReferenceWithdrawCycle.value].cAmount != sp.mutez(0):
                rewards.value = sp.split_tokens(
                    self.data.cycleOperations[currentReferenceWithdrawCycle.value].cAmount, self.data.rate, sp.nat(10000))
                sp.verify(sp.balance-self.data.cycleOperations[currentReferenceWithdrawCycle.value].cAmount > rewards.value +
                          self.data.rewardCarryForwarded, message="Insufficient Contract Balance to transfer the totalRewards of this baking cycle.")

                # for loop used to get all the data pertaining to the different ranges of the cycle whose staking period has just been completed
                sp.for rangeData in self.data.cycleOperations[currentReferenceWithdrawCycle.value].rangeDetails.keys():
                    params = sp.local("params", sp.record(
                        currentReferenceWithdrawCycle=currentReferenceWithdrawCycle.value, rewards=rewards.value, rangeData=rangeData, currentPrice=cp))
                    self.rangeCheck(params.value)

            # Deleting map data that is more than 11 reference cycles old
            sp.if currentReferenceWithdrawCycle.value > 7:
                del self.data.cycleOperations[currentReferenceWithdrawCycle.value-7]
        self.initialiseNewCycleData()


@sp.add_test(name="Test Market")
def test():
    scenario = sp.test_scenario()
    scenario.h1("Market Demo")
    wagerA = sp.test_account("wagerA")
    wagerB = sp.test_account("wagerB")
    wagerC = sp.test_account("wagerC")
    takerA = sp.test_account("takerA")
    takerB = sp.test_account("takerB")
    admin = sp.test_account("admin")
    c1 = StakingMarket(sp.address("tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp"))

    scenario += c1
    scenario += c1.default().run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.addAdmin(sp.address("tz1N2SiwSoTEs8RXKxirYBVN95yoVJuQhPJ2")).run(
        sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.delegate(sp.some(sp.key_hash("tz1YB12JHVHw9GbN66wyfakGYgdTBvokmXQk"))
                            ).run(sender=sp.address("tz1N2SiwSoTEs8RXKxirYBVN95yoVJuQhPJ2"))
    scenario += c1.delegate(sp.none).run(
        sender=sp.address("tz1N2SiwSoTEs8RXKxirYBVN95yoVJuQhPJ2"))
    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.placeBet((0, 250)).run(sender=wagerA, amount=sp.tez(20))
    scenario += c1.collateralize().run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'),
                                       amount=sp.tez(2000))
    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.winningsTransfer(harbingerContractAddress=sp.address("KT1-Harbinger"), asset="XTZ-USD",
                                    targetAddress=sp.address("KT1-SELF")).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.getResponseFromHarbinger(("XTZ-USD", (sp.timestamp(100), sp.nat(
        3680387)))).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))

    scenario += c1.uncollateralize(sp.mutez(500000000), 'tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp').run(
        sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))
    scenario += c1.retrieveToken(address=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'),
                                 amount=sp.mutez(100000000)).run(sender=sp.address('tz1N2dozNmbT8Ds8NAH8TLQTXfuxJoHPT3hp'))