#05-04-2021

import smartpy as sp

class StakePool(sp.Contract):
    
    def __init__(self,admin):
        self.init(admin = sp.set([admin]) , bettors = sp.big_map(tkey = sp.TAddress , tvalue =  sp.TMap(sp.TInt, sp.TRecord(amount = sp.TMutez , range = sp.TPair(sp.TInt,sp.TInt) , stakedAt = sp.TInt ,withdrawn = sp.TBool , withdrawnAmount = sp.TMutez))), roi = sp.pair(sp.int(6) , sp.int(10000)) , betLimit = sp.tez(10), blocksPerCycle=sp.int(4096), rangeStep = sp.int(250) , rangeEnd=sp.int(1000), stakingPeriod = sp.int(2) ,bettingPaused = sp.bool(False),withdrawalsPaused = sp.bool(False),cycleData = sp.big_map(tkey = sp.TInt , tvalue = sp.TRecord(referencePrice = sp.TInt , endingPrice = sp.TInt , concluded = sp.TBool , totalAmount = sp.TMutez ,roi = sp.TPair(sp.TInt , sp.TInt),amountByRange = sp.TMap(sp.TPair(sp.TInt , sp.TInt) , sp.TMutez))))
    
    def initializeInternalMapForNewBettor(self):
        sp.if ~self.data.bettors.contains(sp.sender):
            self.data.bettors[sp.sender] = {}
    
    def betAlreadyPlacedForParticularCycle(self,cycle):
        betsByCycle = self.data.bettors[sp.sender]
        sp.verify(~betsByCycle.contains(cycle), message="You have already placed bet for this cycle.")
    
    def betBelowBetLimit(self):
        sp.verify(sp.amount <= self.data.betLimit , message="Bet more than limit")
        
    def isRangeValid(self,cycle,top,bottom):
        sp.verify(self.data.cycleData[cycle].amountByRange.contains(sp.pair(top , bottom)) , message="Invalid Range")
        
    def isCycleInitiated(self,cycle):
        sp.verify(self.data.cycleData.contains(cycle) , message="Betting not initiated for this cycle.")
        
    def checkBettingPaused(self):
        sp.verify(self.data.bettingPaused == sp.bool(False), message = "Betting is paused by admin.")
        
    def bettorNotAContract(self):
        sp.verify(sp.sender == sp.source , message = "Betting not allowed through contract")
        
    @sp.entry_point
    def placeBet(self,params):
        self.checkBettingPaused()
        self.bettorNotAContract()
        
        sp.verify(sp.amount > sp.mutez(0) , message = "Amount should not be 0")
        currentCycle = sp.local("currentCycle" ,sp.int(0))
        currentCycle = sp.fst(sp.ediv(sp.level,self.data.blocksPerCycle).open_some())
        
        self.initializeInternalMapForNewBettor()
        self.betAlreadyPlacedForParticularCycle(currentCycle+self.data.stakingPeriod)
        self.betBelowBetLimit()
        self.isRangeValid(currentCycle+self.data.stakingPeriod , params.top , params.bottom)
        self.isCycleInitiated(currentCycle+self.data.stakingPeriod)
        
        betsByCycle = self.data.bettors[sp.sender]
        betsByCycle[currentCycle+self.data.stakingPeriod] = sp.record(amount = sp.amount , range = sp.pair(params.top , params.bottom) , withdrawn = sp.bool(False) , withdrawnAmount = sp.mutez(0) , stakedAt = currentCycle)
        
        
        self.data.cycleData[currentCycle+self.data.stakingPeriod].amountByRange[sp.pair(params.top , params.bottom)] += sp.amount
        self.data.cycleData[currentCycle+self.data.stakingPeriod].totalAmount += sp.amount
        
        
    @sp.entry_point
    def getResponseFromHarbinger(self,response):
        sp.verify(self.data.admin.contains(sp.source) , "Un-authorized")
        
        sp.set_type(response , sp.TPair(sp.TString , sp.TPair(sp.TTimestamp , sp.TNat)))
        currentPrice=sp.local("currentPrice",sp.int(0))
        currentPrice = sp.to_int(sp.fst(sp.ediv(sp.snd(sp.snd(response)) , sp.nat(1000)).open_some()))
        
        currentCycle = sp.local("currentCycle" ,sp.int(0))
        currentCycle = sp.fst(sp.ediv(sp.level,self.data.blocksPerCycle).open_some())
        
        sp.verify(~self.data.cycleData.contains(currentCycle+self.data.stakingPeriod))
        
        
        
        rangeMap = sp.local("rangeMap" , sp.map(tkey = sp.TPair(sp.TInt, sp.TInt) , tvalue = sp.TMutez))
        
        iterator = sp.local("iterator" , sp.int(0))
        
        sp.while iterator.value<=self.data.rangeEnd:
            sp.if iterator.value+self.data.rangeStep<=self.data.rangeEnd:
                rangeMap.value[sp.pair(iterator.value,iterator.value+self.data.rangeStep)] =sp.mutez(0)
                rangeMap.value[(sp.int(-1)*(iterator.value+self.data.rangeStep),sp.int(-1)*iterator.value)] =sp.mutez(0)
            #handling extreme ranges initialisation
            sp.else:
                rangeMap.value[(iterator.value,iterator.value)] =sp.mutez(0)
                rangeMap.value[(sp.int(-1)*iterator.value,sp.int(-1)*iterator.value)] =sp.mutez(0)
            iterator.value += self.data.rangeStep
        
        self.data.cycleData[currentCycle+self.data.stakingPeriod] = sp.record(referencePrice = currentPrice , endingPrice = sp.int(0) , concluded = sp.bool(False) , totalAmount = sp.mutez(0) , roi = self.data.roi , amountByRange = rangeMap.value)
        
        #Announce Winning Price
        sp.if self.data.cycleData.contains(currentCycle-1):
            self.data.cycleData[currentCycle-1].endingPrice = currentPrice
            self.data.cycleData[currentCycle-1].concluded = sp.bool(True)
       
    def fetchPriceFromHarbinger(self,harbingerContractAddress , asset , targetAddress):
        contractParams = sp.contract(sp.TPair(sp.TString , sp.TContract(sp.TPair(sp.TString , sp.TPair(sp.TTimestamp , sp.TNat)))) , harbingerContractAddress , entry_point="get").open_some()
        
        callBack = sp.contract(sp.TPair(sp.TString , sp.TPair(sp.TTimestamp , sp.TNat)) , targetAddress , entry_point="getResponseFromHarbinger").open_some()
        
        dataToBeSent = sp.pair(asset , callBack)
        
        sp.transfer(dataToBeSent , sp.mutez(0) , contractParams)
       
    
    @sp.entry_point
    def fetchPriceAndUpdateCycle(self,params):
        sp.verify(self.data.admin.contains(sp.sender), message="Un-Authorized")
        self.fetchPriceFromHarbinger(params.harbingerContractAddress , params.asset , params.targetAddress)
     
        
    def checkConcluded(self,cycle):
        sp.verify(self.data.cycleData[cycle].concluded == sp.bool(True), message = "Cycle has not concluded yet. Please wait.")
    
    def checkAlreadyWithdrawn(self,cycle):
        betsByCycle = self.data.bettors[sp.sender]
        sp.verify(betsByCycle[cycle].withdrawn == sp.bool(False) , message="You have already withdrawn")
        
    def hasWon(self,cycle,range):
        betsByCycle = self.data.bettors[sp.sender]
        betAmount = sp.local("betAmount",sp.mutez(0))
        betAmount = betsByCycle[cycle].amount
        
        totalRewards = sp.local("totalRewards",sp.mutez(0))
        
        totalRewards = sp.split_tokens(self.data.cycleData[cycle].totalAmount , sp.as_nat(sp.fst(self.data.cycleData[cycle].roi)) , sp.as_nat(sp.snd(self.data.cycleData[cycle].roi)))
        
        totalRewards = sp.split_tokens(totalRewards , sp.nat(98) , sp.nat(100))
        
        reward = sp.split_tokens(totalRewards , sp.fst(sp.ediv(betAmount , sp.mutez(1)).open_some()) , sp.fst(sp.ediv(self.data.cycleData[cycle].amountByRange[range],sp.mutez(1)).open_some()) )
        
        betsByCycle[cycle].withdrawn=True
        betsByCycle[cycle].withdrawnAmount = betsByCycle[cycle].amount + reward
        sp.send(sp.sender , betsByCycle[cycle].amount + reward)
    
    def hasLost(self,cycle):
        betsByCycle = self.data.bettors[sp.sender]
        betsByCycle[cycle].withdrawn=True
        betsByCycle[cycle].withdrawnAmount = betsByCycle[cycle].amount
        sp.send(sp.sender,betsByCycle[cycle].amount)
        
        
        
    def checkIfWinnerAndDisburse(self,cycle):
        change = sp.local("change",sp.int(0))
        change = self.data.cycleData[cycle].endingPrice - self.data.cycleData[cycle].referencePrice
        changePercentQuotient = sp.local("changePercentQuotient",sp.int(0))
        changePercentQuotient.value = sp.mul(change , 10000)
        changePercentQuotient.value = sp.fst(sp.ediv(changePercentQuotient.value,self.data.cycleData[cycle].referencePrice).open_some())
        
        upperLimit = sp.local("upperLimit",sp.int(0))
        lowerLimit = sp.local("lowerLimit",sp.int(0))
        
        betsByCycle = self.data.bettors[sp.sender]
        lowerLimit = sp.fst(betsByCycle[cycle].range)
        upperLimit = sp.snd(betsByCycle[cycle].range)
        
        
        sp.if upperLimit != lowerLimit:
            sp.if lowerLimit<= changePercentQuotient.value:
                sp.if changePercentQuotient.value<upperLimit:
                    self.hasWon(cycle,betsByCycle[cycle].range)
                sp.else:
                    self.hasLost(cycle)
            sp.else:
                self.hasLost(cycle)
        sp.else:
            sp.if lowerLimit < 0:
                sp.if lowerLimit>changePercentQuotient.value:
                    self.hasWon(cycle,betsByCycle[cycle].range)
                sp.else:
                    self.hasLost(cycle)
            sp.else:
                sp.if lowerLimit<changePercentQuotient.value:
                    self.hasWon(cycle,betsByCycle[cycle].range)
                sp.else:
                    self.hasLost(cycle)
                    
    def checkWithdrawalsPaused(self):
        sp.verify(self.data.withdrawalsPaused == sp.bool(False), message = "Withdrawals are paused by admin.")
                    
    @sp.entry_point
    def withdrawAmount(self,params):
        self.checkWithdrawalsPaused()
        self.checkConcluded(params.cycle)
        self.checkAlreadyWithdrawn(params.cycle)
        self.checkIfWinnerAndDisburse(params.cycle)


    @sp.entry_point
    def default(self):
        sp.verify(sp.amount > sp.mutez(0), "Please send atleast 1 mutez")
        
    @sp.entry_point
    def changeBettingPauseState(self):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        self.data.bettingPaused = ~self.data.bettingPaused
        
    @sp.entry_point
    def changeWithdrawalsPauseState(self):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        self.data.withdrawalsPaused = ~self.data.withdrawalsPaused
    
    @sp.entry_point
    def addAdmin(self,params):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        self.data.admin.add(params.address)
        
    @sp.entry_point
    def removeAdmin(self,params):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        self.data.admin.remove(params.address)
        
    @sp.entry_point
    def changeROI(self,params):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        self.data.roi = sp.pair(params.numerator , params.denominator)
        
    @sp.entry_point
    def changeBetRange(self,params):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        self.data.rangeStep = params.step
        self.data.rangeEnd = params.end
        
    @sp.entry_point
    def changeBlocksPerCycle(self,params):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        self.data.blocksPerCycle = params.blocksPerCycle
        
    @sp.entry_point
    def depositXTZ(self):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        
    @sp.entry_point
    def recoverXTZ(self,params):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        sp.send(sp.sender , params.amount)
        
    @sp.entry_point
    def changeBetLimit(self,params):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        self.data.betLimit = params.betLimit
    
    @sp.entry_point
    def delegate(self, baker):
        sp.verify(self.data.admin.contains(sp.sender) , message = "Un-Authorized")
        sp.set_delegate(baker)
        
        
@sp.add_test(name = "test")
def test():
    
    obj = StakePool(sp.address("tz1-Admin"))
    scenario = sp.test_scenario()
    scenario += obj
    
    scenario += obj.depositXTZ().run(sender = sp.address("tz1-Admin") , amount = sp.tez(1000))
    
    scenario += obj.recoverXTZ(amount = sp.tez(500)).run(sender = sp.address("tz1-Admin"))
    
    # Cycle - 63 Ongoing 
    # Betting Intitation 63 -> 65
    #scenario += obj.updatePrice(price = sp.int(4000)).run(level = 129661 ,sender = sp.address("tz1-Admin"))
    scenario += obj.fetchPriceAndUpdateCycle(asset = "XTZ-USD" , harbingerContractAddress = sp.address("KT1-Normalizer-Harbinger") , targetAddress = sp.address("KT1-SELF")).run(sender = sp.address("tz1-Admin"))
    scenario += obj.getResponseFromHarbinger(("XTZ-USD" , (sp.timestamp(0) , sp.nat(4000000)))).run(level = 129661 ,sender = sp.address("KT1-Normalizer-Harbinger") ,source= sp.address("tz1-Admin"))
    
    #Placing Bet
    scenario += obj.placeBet(top = sp.int(0) , bottom = sp.int(250)).run(sender = sp.address("tz1-Bob") , amount = sp.tez(2) , level = 129668)
    
    scenario += obj.placeBet(top = sp.int(0) , bottom = sp.int(250)).run(sender = sp.address("tz1-Mark") , amount = sp.tez(2) , level = 129667)

    
    scenario += obj.placeBet(top = sp.int(-250) , bottom = sp.int(0)).run(sender = sp.address("tz1-Alice") , amount = sp.tez(2) , level = 129670)
    
    scenario += obj.placeBet(top = sp.int(250) , bottom = sp.int(500)).run(sender = sp.address("tz1-Joe") , amount = sp.tez(3) , level = 129671)
    
    scenario += obj.placeBet(top = sp.int(250) , bottom = sp.int(500)).run(sender = sp.address("tz1-John") , amount = sp.tez(4) , level = 129672)
    
    scenario += obj.placeBet(top = sp.int(1000) , bottom = sp.int(1000)).run(sender = sp.address("tz1-Elan") , amount = sp.tez(4) , level = 129672)
    
    # Cycle - 64 Ongoing 
    # Betting Intitation 64 -> 66
    # scenario += obj.updatePrice(price = sp.int(3900)).run(level = 131720 , sender = sp.address("tz1-Admin"))
    
    scenario += obj.fetchPriceAndUpdateCycle(asset = "XTZ-USD" , harbingerContractAddress = sp.address("KT1-Normalizer-Harbinger") , targetAddress = sp.address("KT1-SELF")).run(sender = sp.address("tz1-Admin"))
    scenario += obj.getResponseFromHarbinger(("XTZ-USD" , (sp.timestamp(0) , sp.nat(3900000)))).run(level = 131720 ,sender = sp.address("KT1-Normalizer-Harbinger") ,source= sp.address("tz1-Admin"))
    
    
    #Placing Bet
    scenario += obj.placeBet(top = sp.int(0) , bottom = sp.int(250)).run(sender = sp.address("tz1-Bob") , amount = sp.tez(4) , level = 131721)
    
    scenario += obj.placeBet(top = sp.int(0) , bottom = sp.int(250)).run(sender = sp.address("tz1-Mark") , amount = sp.tez(3) , level = 131722)

    
    scenario += obj.placeBet(top = sp.int(-250) , bottom = sp.int(0)).run(sender = sp.address("tz1-Alice") , amount = sp.tez(1) , level = 131723)
    
    scenario += obj.placeBet(top = sp.int(250) , bottom = sp.int(500)).run(sender = sp.address("tz1-Joe") , amount = sp.tez(6) , level = 131724)
    
    scenario += obj.placeBet(top = sp.int(-750) , bottom = sp.int(-500)).run(sender = sp.address("tz1-John") , amount = sp.tez(9) , level = 131725)
    
    scenario += obj.placeBet(top = sp.int(1000) , bottom = sp.int(1000)).run(sender = sp.address("tz1-Elan") , amount = sp.tez(5) , level = 131726)
    
    # Cycle - 65 Ongoing
    # Betting Intitation 65 -> 67
    #scenario += obj.updatePrice(price = sp.int(3900)).run(level = 133220 , sender = sp.address("tz1-Admin"))
    
    scenario += obj.fetchPriceAndUpdateCycle(asset = "XTZ-USD" , harbingerContractAddress = sp.address("KT1-Normalizer-Harbinger") , targetAddress = sp.address("KT1-SELF")).run(sender = sp.address("tz1-Admin"))
    scenario += obj.getResponseFromHarbinger(("XTZ-USD" , (sp.timestamp(0) , sp.nat(3900000)))).run(level = 133220 ,sender = sp.address("KT1-Normalizer-Harbinger") ,source= sp.address("tz1-Admin"))
    
    
    #Placing Bet
    scenario += obj.placeBet(top = sp.int(0) , bottom = sp.int(250)).run(sender = sp.address("tz1-Bob") , amount = sp.tez(7) , level = 133221)
    
    scenario += obj.placeBet(top = sp.int(0) , bottom = sp.int(250)).run(sender = sp.address("tz1-Mark") , amount = sp.tez(6) , level = 133222)

    
    scenario += obj.placeBet(top = sp.int(-250) , bottom = sp.int(0)).run(sender = sp.address("tz1-Alice") , amount = sp.tez(5) , level = 133223)
    
    scenario += obj.placeBet(top = sp.int(250) , bottom = sp.int(500)).run(sender = sp.address("tz1-Joe") , amount = sp.tez(8) , level = 133224)
    
    scenario += obj.placeBet(top = sp.int(1000) , bottom = sp.int(1000)).run(sender = sp.address("tz1-John") , amount = sp.tez(7) , level = 133225)
    
    scenario += obj.placeBet(top = sp.int(1000) , bottom = sp.int(1000)).run(sender = sp.address("tz1-Elan") , amount = sp.tez(9) , level = 133226)
    
    # Cycle - 66 Ongoing
    # Changing prediction ranges
    scenario += obj.changeBetRange(step=300,end=1200).run(sender=sp.address("tz1-Admin"))
    # Betting Intitation 66 -> 68
    # Concluding 65 
    #scenario += obj.updatePrice(price = sp.int(4050)).run(level = 135268,sender = sp.address("tz1-Admin"))
    
    scenario += obj.fetchPriceAndUpdateCycle(asset = "XTZ-USD" , harbingerContractAddress = sp.address("KT1-Normalizer-Harbinger") , targetAddress = sp.address("KT1-SELF")).run(sender = sp.address("tz1-Admin"))
    scenario += obj.getResponseFromHarbinger(("XTZ-USD" , (sp.timestamp(0) , sp.nat(4050000)))).run(level = 135268 ,sender = sp.address("KT1-Normalizer-Harbinger") ,source= sp.address("tz1-Admin"))
    
    
    
    #Placing Bet
    scenario += obj.placeBet(top = sp.int(0) , bottom = sp.int(300)).run(sender = sp.address("tz1-Bob") , amount = sp.tez(7) , level = 135270)
    
    scenario += obj.placeBet(top = sp.int(300) , bottom = sp.int(600)).run(sender = sp.address("tz1-Mark") , amount = sp.tez(6) , level = 135271)

    
    scenario += obj.placeBet(top = sp.int(-600) , bottom = sp.int(-300)).run(sender = sp.address("tz1-Alice") , amount = sp.tez(5) , level = 135272)
    
    scenario += obj.placeBet(top = sp.int(-1200) , bottom = sp.int(-1200)).run(sender = sp.address("tz1-Joe") , amount = sp.tez(8) , level = 135273)
    
    scenario += obj.placeBet(top = sp.int(1200) , bottom = sp.int(1200)).run(sender = sp.address("tz1-John") , amount = sp.tez(7) , level = 135274)
    
    scenario += obj.placeBet(top = sp.int(0) , bottom = sp.int(300)).run(sender = sp.address("tz1-Elan") , amount = sp.tez(9) , level = 135275)
    
    # Withdrawals of 65
    scenario += obj.withdrawAmount(cycle = sp.int(65)).run(sender = sp.address("tz1-Alice"))
    scenario += obj.withdrawAmount(cycle = sp.int(65)).run(sender = sp.address("tz1-Bob"))
    scenario += obj.withdrawAmount(cycle = sp.int(65)).run(sender = sp.address("tz1-Joe"))
    scenario += obj.withdrawAmount(cycle = sp.int(65)).run(sender = sp.address("tz1-John"))
    scenario += obj.withdrawAmount(cycle = sp.int(65)).run(sender = sp.address("tz1-Mark"))
    scenario += obj.withdrawAmount(cycle = sp.int(65)).run(sender = sp.address("tz1-Elan"))
    
    # Cycle - 67 Ongoing
    # Changing prediction ranges
    scenario += obj.changeBetRange(step=400,end=2000).run(sender=sp.address("tz1-Admin"))
    # Betting Intitation 66 -> 69
    # Concluding 66
    #scenario += obj.updatePrice(price = sp.int(3700)).run(level = 137316,sender = sp.address("tz1-Admin"))
    
    scenario += obj.fetchPriceAndUpdateCycle(asset = "XTZ-USD" , harbingerContractAddress = sp.address("KT1-Normalizer-Harbinger") , targetAddress = sp.address("KT1-SELF")).run(sender = sp.address("tz1-Admin"))
    scenario += obj.getResponseFromHarbinger(("XTZ-USD" , (sp.timestamp(0) , sp.nat(3700000)))).run(level = 137316 ,sender = sp.address("KT1-Normalizer-Harbinger") ,source= sp.address("tz1-Admin"))
    
    
    #Placing Bet
    scenario += obj.placeBet(top = sp.int(0) , bottom = sp.int(400)).run(sender = sp.address("tz1-Bob") , amount = sp.tez(7) , level = 137320)
    
    scenario += obj.placeBet(top = sp.int(800) , bottom = sp.int(1200)).run(sender = sp.address("tz1-Mark") , amount = sp.tez(6) , level = 137321)

    
    scenario += obj.placeBet(top = sp.int(-800) , bottom = sp.int(-400)).run(sender = sp.address("tz1-Alice") , amount = sp.tez(5) , level = 137322)
    
    scenario += obj.placeBet(top = sp.int(-1200) , bottom = sp.int(-800)).run(sender = sp.address("tz1-Joe") , amount = sp.tez(8) , level = 137323)
    
    scenario += obj.placeBet(top = sp.int(2000) , bottom = sp.int(2000)).run(sender = sp.address("tz1-John") , amount = sp.tez(7) , level = 137324)
    
    scenario += obj.placeBet(top = sp.int(800) , bottom = sp.int(1200)).run(sender = sp.address("tz1-Elan") , amount = sp.tez(9) , level = 137325)
    
    # Betting not allowed through contract
    scenario += obj.placeBet(top = sp.int(800) , bottom = sp.int(1200)).run(source = sp.address("KT1-Jane") , sender = sp.address("tz1-Jane") , amount = sp.tez(9) , level = 137326 ,valid=False)
    
    # Withdrawals of 66
    scenario += obj.withdrawAmount(cycle = sp.int(66)).run(sender = sp.address("tz1-Alice"))
    scenario += obj.withdrawAmount(cycle = sp.int(66)).run(sender = sp.address("tz1-Bob"))
    scenario += obj.withdrawAmount(cycle = sp.int(66)).run(sender = sp.address("tz1-Joe"))
    scenario += obj.withdrawAmount(cycle = sp.int(66)).run(sender = sp.address("tz1-John"))
    scenario += obj.withdrawAmount(cycle = sp.int(66)).run(sender = sp.address("tz1-Mark"))
    scenario += obj.withdrawAmount(cycle = sp.int(66)).run(sender = sp.address("tz1-Elan"))
    
    # Cycle - 68 Ongoing
    # Betting Intitation 68 -> 70
    # Concluding 67
    #scenario += obj.updatePrice(price = sp.int(5000)).run(level = 140264,sender = sp.address("tz1-Admin"))
    
    scenario += obj.fetchPriceAndUpdateCycle(asset = "XTZ-USD" , harbingerContractAddress = sp.address("KT1-Normalizer-Harbinger") , targetAddress = sp.address("KT1-SELF")).run(sender = sp.address("tz1-Admin"))
    scenario += obj.getResponseFromHarbinger(("XTZ-USD" , (sp.timestamp(0) , sp.nat(5000000)))).run(level = 140264 ,sender = sp.address("KT1-Normalizer-Harbinger") ,source= sp.address("tz1-Admin"))
    
    
    # Withdrawals of 67
    scenario += obj.withdrawAmount(cycle = sp.int(67)).run(sender = sp.address("tz1-Alice"))
    scenario += obj.withdrawAmount(cycle = sp.int(67)).run(sender = sp.address("tz1-Bob"))
    scenario += obj.withdrawAmount(cycle = sp.int(67)).run(sender = sp.address("tz1-Joe"))
    scenario += obj.withdrawAmount(cycle = sp.int(67)).run(sender = sp.address("tz1-John"))
    scenario += obj.withdrawAmount(cycle = sp.int(67)).run(sender = sp.address("tz1-Mark"))
    scenario += obj.withdrawAmount(cycle = sp.int(67)).run(sender = sp.address("tz1-Elan"))
    
    # Cycle - 69 Ongoing
    # Betting Intitation 69 -> 71
    # Concluding 68
    #scenario += obj.updatePrice(price = sp.int(4233)).run(level = 141412,sender = sp.address("tz1-Admin"))
    
    scenario += obj.fetchPriceAndUpdateCycle(asset = "XTZ-USD" , harbingerContractAddress = sp.address("KT1-Normalizer-Harbinger") , targetAddress = sp.address("KT1-SELF")).run(sender = sp.address("tz1-Admin"))
    scenario += obj.getResponseFromHarbinger(("XTZ-USD" , (sp.timestamp(0) , sp.nat(4233000)))).run(level = 141412 ,sender = sp.address("KT1-Normalizer-Harbinger") ,source= sp.address("tz1-Admin"))
    
    
    # Withdrawals of 68
    scenario += obj.withdrawAmount(cycle = sp.int(68)).run(sender = sp.address("tz1-Alice"))
    scenario += obj.withdrawAmount(cycle = sp.int(68)).run(sender = sp.address("tz1-Bob"))
    scenario += obj.withdrawAmount(cycle = sp.int(68)).run(sender = sp.address("tz1-Joe"))
    scenario += obj.withdrawAmount(cycle = sp.int(68)).run(sender = sp.address("tz1-John"))
    scenario += obj.withdrawAmount(cycle = sp.int(68)).run(sender = sp.address("tz1-Mark"))
    scenario += obj.withdrawAmount(cycle = sp.int(68)).run(sender = sp.address("tz1-Elan"))
    
    # Duplicate Withdrawal
    scenario += obj.withdrawAmount(cycle = sp.int(68)).run(sender = sp.address("tz1-Elan") , valid = False)
    
    # Cycle - 70 Ongoing
    # Betting Intitation 70 -> 72
    # Concluding 69
    #scenario += obj.updatePrice(price = sp.int(4070)).run(level = 143460,sender = sp.address("tz1-Admin"))
    
    scenario += obj.fetchPriceAndUpdateCycle(asset = "XTZ-USD" , harbingerContractAddress = sp.address("KT1-Normalizer-Harbinger") , targetAddress = sp.address("KT1-SELF")).run(sender = sp.address("tz1-Admin"))
    scenario += obj.getResponseFromHarbinger(("XTZ-USD" , (sp.timestamp(0) , sp.nat(4070000)))).run(level = 143460 ,sender = sp.address("KT1-Normalizer-Harbinger") ,source= sp.address("tz1-Admin"))
    
    
    # Withdrawals of 69
    scenario += obj.withdrawAmount(cycle = sp.int(69)).run(sender = sp.address("tz1-Alice"))
    scenario += obj.withdrawAmount(cycle = sp.int(69)).run(sender = sp.address("tz1-Bob"))
    scenario += obj.withdrawAmount(cycle = sp.int(69)).run(sender = sp.address("tz1-Joe"))
    scenario += obj.withdrawAmount(cycle = sp.int(69)).run(sender = sp.address("tz1-John"))
    scenario += obj.withdrawAmount(cycle = sp.int(69)).run(sender = sp.address("tz1-Mark"))
    scenario += obj.withdrawAmount(cycle = sp.int(69)).run(sender = sp.address("tz1-Elan"))
    
    
    
    # Admin Only Funstions Test
    
    scenario += obj.changeBettingPauseState().run(sender=sp.address("tz1-Admin"))
    scenario += obj.changeBettingPauseState().run(sender=sp.address("tz1-Admin"))
    scenario += obj.changeWithdrawalsPauseState().run(sender = sp.address("tz1-Admin"))
    scenario += obj.changeWithdrawalsPauseState().run(sender = sp.address("tz1-Admin"))
    
    scenario += obj.addAdmin(address = sp.address("tz1-Admin-2")).run(sender=sp.address("tz1-Admin"))
    scenario += obj.addAdmin(address = sp.address("tz1-Admin-3")).run(sender=sp.address("tz1-Admin"))
    scenario += obj.removeAdmin(address = sp.address("tz1-Admin-3")).run(sender=sp.address("tz1-Admin"))
    
    scenario += obj.changeROI(numerator = 400 , denominator = 100000).run(sender=sp.address("tz1-Admin"))
    scenario += obj.changeROI(numerator = 588 , denominator = 100000).run(sender=sp.address("tz1-Admin"))
    
    scenario += obj.changeBetRange(step=300,end=1200).run(sender=sp.address("tz1-Admin"))
    
    scenario += obj.changeBetRange(step=250,end=1000).run(sender=sp.address("tz1-Admin"))
    
    scenario += obj.changeBlocksPerCycle(blocksPerCycle = sp.int(4096)).run(sender=sp.address("tz1-Admin"))
    
    scenario += obj.changeBlocksPerCycle(blocksPerCycle = sp.int(2048)).run(sender=sp.address("tz1-Admin"))
    
    scenario += obj.changeBetLimit(betLimit = sp.tez(100)).run(sender=sp.address("tz1-Admin"))
    
    scenario += obj.delegate(sp.some(sp.key_hash("tz1-Baker"))).run(sender=sp.address("tz1-Admin"))
    
    
    
    