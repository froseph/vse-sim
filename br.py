from mydecorators import autoassign, cached_property, curried
import random
from numpy.lib.scimath import sqrt
from numpy.core.fromnumeric import mean, std
from numpy.lib.function_base import median
from numpy.ma.core import floor

class Voter(tuple):
    """A tuple of candidate utilities.
    
    

    """
    
    @classmethod
    def rand(cls, ncand):
        """Create a random voter with standard normal utilities.
        
        ncand determines how many utilities a voter should have
            >>> [len(Voter.rand(i)) for i in list(range(5))]
            [0, 1, 2, 3, 4]
        
        utilities should be in a standard normal distribution
            >>> v100 = Voter.rand(100)
            >>> -0.3 < mean(v100) < 0.3
            True
            >>> 0.8 < std(v100) < 1.2
            True
        """
        return cls(random.gauss(0,1) for i in range(ncand))
        
    
    def hybridWith(self, v2, w2):
        """Create a weighted average of two voters. 
        
        The weight of v1 is always 1; w2 is the weight of v2 relative to that.
        
        If both are
        standard normal to start with, the result will be standard normal too.
        
        Length must be the same
            >>> Voter([1,2]).hybridWith(Voter([1,2,3]),1)
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
              File "./br.py", line 42, in hybridWith
                assert len(self) == len(v2)
            AssertionError

        A couple of basic sanity checks:
            >>> v2 = Voter([1,2]).hybridWith(Voter([3,2]),1)
            >>> [round(u,5) for u in v2.hybridWith(v2,1)]
            [4.0, 4.0]
            >>> Voter([1,2,5]).hybridWith(Voter([-0.5,-1,0]),0.75)
            (0.5, 1.0, 4.0)
        """
        assert len(self) == len(v2)
        return self.copyWithUtils(  ((self[i] / sqrt(1 + w2 ** 2)) + 
                                    (w2 * v2[i] / sqrt(1 + w2 ** 2)))
                                 for i in range(len(self)))
            
    def copyWithUtils(self, utils):
        """create a new voter with attrs as self and given utils.
        
        This version is a stub, since this voter class has no attrs."""
        return self.__class__(utils)
    
    def mutantChild(self, muteWeight):
        """Returns a copy hybridized with a random voter of weight muteWeight.
        
        Should remain standard normal:
            >>> v100 = Voter.rand(100)
            >>> for i in range(30):
            ...     v100 = v100.mutantChild(random.random())
            ... 
            >>> -0.3 < mean(v100) < 0.3
            True
            >>> 0.8 < std(v100) < 1.2
            True

        """
        return self.hybridWith(self.__class__.rand(len(self)), muteWeight)
    
    def isNormal(self):
        pass
    
class PersonalityVoter(Voter):
    
    cluster_count = 0
    
    @classmethod
    def rand(cls, ncand):
        voter = super().rand(ncand)
        voter.cluster = cls.cluster_count
        cls.cluster_count += 1
        voter.personality = random.gauss(0,1) #probably to be used for strategic propensity
        #but in future, could be other clustering voter variability, such as media awareness
        return voter
    
    def copyWithUtils(self, utils):
        voter = super().copyWithUtils(self, utils)
        voter.personality = self.personality
        voter.cluster = self.cluster
        return voter
            
class Electorate(list):
    """A list of voters.
    Each voter is a list of candidate utilities"""
    @cached_property
    def socUtils(self):
        """Just get the social utilities.
        
        >>> e = Electorate([[1,2],[3,4]])
        >>> e.socUtils
        [2.0, 3.0]
        """
        return list(map(mean,zip(*self)))
    
class RandomModel:
    """Empty base class for election models; that is, electorate factories.
    
    >>> e4 = RandomModel()(4,3)
    >>> [len(v) for v in e4]
    [3, 3, 3, 3]
    """
    def __call__(self, nvot, ncand, vType=Voter):
        return Electorate(vType.rand(ncand) for i in range(nvot))
    
class ReverseModel(RandomModel):
    """Creates an even number of voters in two diametrically-opposed camps
    (ie, opposite utilities for all candidates)
    
    >>> e4 = ReverseModel()(4,3)
    >>> [len(v) for v in e4]
    [3, 3, 3, 3]
    >>> e4[0].hybridWith(e4[3],1)
    (0.0, 0.0, 0.0)
    """
    def __call__(self, nvot, ncand, vType=Voter):
        if nvot % 2:
            raise ValueError
        basevoter = vType.rand(ncand)
        return Electorate( ([basevoter] * (nvot//2)) + 
                           ([vType(-q for q in basevoter)] * (nvot//2))
                        )

class QModel(RandomModel):
    """Adds a quality dimension to a base model,
    by generating an election and then hybridizing all voters
    with a common quality vector.
    
    Useful along with ReverseModel to create a poor-man's 2d model.
    
    Basic structure
        >>> e4 = QModel(sqrt(3), RandomModel())(100,1)
        >>> len(e4)
        100
        >>> len(e4.socUtils)
        1
        
    Reduces the standard deviation
        >>> 0.4 < std(list(zip(e4))) < 0.6
        True

    """
    @autoassign
    def __init__(self, qWeight=1, baseModel=ReverseModel()):
        pass
    
    def __call__(self, nvot, ncand, vType=Voter):
        qualities = vType.rand(ncand)
        return Electorate([v.hybridWith(qualities,self.qWeight)
                for v in self.baseModel(nvot, ncand, vType)])


class PolyaModel(RandomModel):
    """This creates electorates based on a Polya/Hoppe/Dirchlet model, with mutation.
    You start with an "urn" of n=seedVoter voters from seedModel,
     plus alpha "wildcard" voters. Then you draw a voter from the urn, 
     clone and mutate them, and put the original and clone back into the urn.
     If you draw a "wildcard", use voterGen to make a new voter.
     """
    @autoassign
    def __init__(self, seedVoters=2, alpha=1, seedModel=QModel(),
                 mutantFactor=0.2):
        pass
    
    def __call__(self, nvot, ncand, vType=Voter):
        """Tests? Making statistical tests that would pass reliably is
        a huge hassle. Sorry, maybe later.
        """
        election = self.seedModel(self.seedVoters, ncand, vType)
        while len(election) < nvot:
            i = random.randrange(len(election) + self.alpha)
            if i < len(election):
                election.append(election[i].mutantChild(self.mutantFactor))
            else:
                election.append(vType.rand(ncand))
        return election

class Method:
    """Base class for election methods. Holds the duct tape."""
    
    def results(self, ballots):
        """Combines ballots into results. Override for comparative
        methods.
        
        Test for subclasses, makes no sense in this abstract base class.
        """
        if type(ballots) is not list:
            ballots = list(ballots)
        return list(map(self.candScore,zip(*ballots)))
    
    def winner(self, results):
        """Simply find the winner once scores are already calculated. Override for
        ranked methods.
        

        >>> Method().winner([1,2,3,2,-100])
        2
        >>> 2 < Method().winner([1,2,1,3,3,3,2,1,2]) < 6
        True
        """
        winScore = max(results)
        winners = [cand for (cand, score) in enumerate(results) if score==winScore]
        return random.choice(winners)
    
    def resultsFor(self, voters, makeBallot):
        """create ballots and get results. 
        
        Again, test on subclasses.
        """
        return self.results(makeBallot(self.__class__, voter) for voter in voters)
        
    def multiResults(self, voters, media=lambda x:x):
        """Runs two elections: first with honest votes, then
        with strategic results based on the first results (filtered by
        the media).
        
        Returns a tuple of (honResults, stratResults). The stratresults
        are based on common information, which is given by media(honresults).
        """
        hon = self.resultsFor(voters, self.honBallot)
        info = media(hon)
        strat = self.resultsFor(voters, self.stratBallotFor(info))
        oss = self.resultsFor(voters, self.ossBallot)
        return (hon, strat, oss)
        
    def vseOn(self, voters):
        """Finds honest and strategic voter satisfaction efficiency (VSE) 
        for this method on the given electorate.
        """
        multiResults = self.multiResults(voters)
        utils = voters.socUtils
        best = max(utils)
        rand = mean(utils)
        
        return (((utils[self.winner(result)] - rand) / (best - rand)) 
                for result in results) + (self.__class__.__name__,)
    
    @staticmethod #cls is provided explicitly, not through binding
    def ossBallot(cls, voter):
        """one-sided strategy:
        returns a 'strategic' ballot for those who prefer the honest runner-up,
        and an honest ballot for those who prefer the honest winner. Only works
        if honBallot and stratBallot have already been called for the voter.
        """
        cname = cls.__name__
        if getattr(voter, cname + "_isStrat", False):
            res = getattr(voter, cname + "_strat")
        else:
            res = getattr(voter, cname + "_hon")
        return res
    
def rememberBallot(fun):
    """A decorator for a function of the form xxxBallot(cls, voter)
    which memoizes the vote onto the voter in an attribute named <methName>_xxx
    """
    def getAndRemember(cls, voter):
        ballot = fun(cls, voter)
        setattr(voter, cls.__name__ + "_" + fun.__name__[:-6], ballot) #leave off the "...Ballot" 
        return ballot
    return getAndRemember

class Score(Method): 
    """Score voting, 0-10."""
    candScore = staticmethod(mean)
        #"""Takes the list of votes for a candidate; returns the candidate's score."""

    @staticmethod #cls is provided explicitly, not through binding
    @rememberBallot
    def honBallot(cls, utils):
        """Takes utilities and returns an honest ballot (on 0..10)"""
        bot = min(utils)
        scale = max(utils)-bot
        return [floor(10.99 * (util-bot) / scale) for util in utils]
    
    def stratBallotFor(self, info):
        """Returns a (function which takes utilities and returns a strategic ballot)
        for the given "polling" info.""" 
        
        places = sorted(enumerate(info),key=lambda x:x[0]) #from high to low
        #print("placesxx",places)
        frontrunners = places[0][0], places[1][0]
        @rememberBallot
        def stratBallot(cls, voter, front=frontrunners):
            cuts = [voter[front[0]], voter[front[1]]]
            if cuts[0] == cuts[1]:
                return [(10 if (util >= cuts[0]) else 0) for util in voter]
            else:
                if cuts[0] > cuts[1]:
                    #winner is preferred; be complacent.
                    strat = False
                else:
                    #runner-up is preferred; be strategic in iss run
                    strat = True
                    #sort cuts high to low
                    cuts = (cuts[1], cuts[0])
                setattr(voter, cls.__name__ + "_isStrat", strat)
                return [max(0,min(10,floor(
                                10.99 * (util-cuts[1]) / (cuts[0]-cuts[1])
                            ))) 
                        for util in voter]
        return stratBallot
    
    

def toVote(cutoffs, util):
    """maps one util to a vote, using cutoffs.
    
    Used by Mav, but declared outside to avoid method binding overhead."""
    for vote in range(len(cutoffs)):
        if util <= cutoffs[vote]:
            return vote
    return vote + 1
    

class Mav(Method):
    baseCuts = [-0.8, 0, 0.8, 1.6]
    def candScore(self, scores):
        """For now, only works correctly for odd nvot"""
        scores = sorted(scores)
        nvot = len(scores)
        i = mid = nvot // 2
        base = scores[i]
        while (i < nvot and scores[i] == base):
            i += 1
        mod = mid * (base + 0.5) / (i - 0.5)
        if mod > base:
            return mod
        return base - ((base - mod) / (base + 0.5)) 
    
    @staticmethod #cls is provided explicitly, not through binding
    @rememberBallot
    def honBallot(cls, voter):
        """Takes utilities and returns an honest ballot (on 0..4)"""
        cutoffs = cls.baseCuts[0:3] + [max(voter)]
        return [toVote(cutoffs, util) for util in voter]
        
    
    def stratBallotFor(self, info):
        """Returns a (function which takes utilities and returns a strategic ballot)
        for the given "polling" info.""" 
        places = sorted(enumerate(info),key=lambda x:x[0]) #from high to low
        #print("places",places)
        frontrunners = (places[0][0], places[1][0], places[0][1], places[1][1])
        
        @rememberBallot
        def stratBallot(cls, voter, front=frontrunners):
            frontUtils = [voter[front[0]], voter[front[1]]] #utils of frontrunners
            if frontUtils[0] == frontUtils[1]:
                return [(4 if (util >= frontUtils[0]) else 0) for util in voter]
            else:
                if frontUtils[0] > frontUtils[1]:
                    #winner is preferred; be complacent.
                    strat = False
                else:
                    #runner-up is preferred; be strategic in iss run
                    strat = True
                    #sort cuts high to low
                    frontUtils = (frontUtils[1], frontUtils[0])
                setattr(voter, cls.__name__ + "_isStrat", strat)
                top = max(voter)
                cutoffs = [(  (min(frontUtils[0], self.baseCuts[i])) 
                                 if (i < floor(front[3]) - 1) else 
                            ( (frontUtils[1]) 
                                 if (i < floor(front[2]) + 1) else
                              min(top, self.baseCuts[i])
                              ))
                           for i in range(4)]
                return [toVote(cutoffs, util) for util in voter]
        return stratBallot
        
        
class Mav(Method):
    baseCuts = [-0.8, 0, 0.8, 1.6]
    def candScore(self, scores):
        """For now, only works correctly for odd nvot"""
        scores = sorted(scores)
        nvot = len(scores)
        i = mid = nvot // 2
        base = scores[i]
        while (i < nvot and scores[i] == base):
            i += 1
        mod = mid * (base + 0.5) / (i - 0.5)
        if mod > base:
            return mod
        return base - ((base - mod) / (base + 0.5)) 
    
    @staticmethod #cls is provided explicitly, not through binding
    @rememberBallot
    def honBallot(cls, voter):
        """Takes utilities and returns an honest ballot (on 0..4)"""
        cutoffs = cls.baseCuts[0:3] + [max(voter)]
        return [toVote(cutoffs, util) for util in voter]
        
    
    def stratBallotFor(self, info):
        """Returns a (function which takes utilities and returns a strategic ballot)
        for the given "polling" info.""" 
        places = sorted(enumerate(info),key=lambda x:x[0]) #from high to low
        #print("places",places)
        frontrunners = (places[0][0], places[1][0], places[0][1], places[1][1])
        
        @rememberBallot
        def stratBallot(cls, voter, front=frontrunners):
            frontUtils = [voter[front[0]], voter[front[1]]] #utils of frontrunners
            if frontUtils[0] == frontUtils[1]:
                return [(4 if (util >= frontUtils[0]) else 0) for util in voter]
            else:
                if frontUtils[0] > frontUtils[1]:
                    #winner is preferred; be complacent.
                    strat = False
                else:
                    #runner-up is preferred; be strategic in iss run
                    strat = True
                    #sort cuts high to low
                    frontUtils = (frontUtils[1], frontUtils[0])
                setattr(voter, cls.__name__ + "_isStrat", strat)
                top = max(voter)
                cutoffs = [(  (min(frontUtils[0], self.baseCuts[i])) 
                                 if (i < floor(front[3]) - 1) else 
                            ( (frontUtils[1]) 
                                 if (i < floor(front[2]) + 1) else
                              min(top, self.baseCuts[i])
                              ))
                           for i in range(4)]
                return [toVote(cutoffs, util) for util in voter]
        return stratBallot
        
class Mj(Mav):
    """CURRENTLY BADLY INCOMPLETE; JUST A COPY OF MAV"""
    def candScore(self, scores):
        """This formula will always give numbers within 0.5 of the raw median.
        Unfortunately, with 5 grade levels, these will tend to be within 0.1 of
        the raw median, leaving scores further from the integers mostly unused.
        This is only a problem aesthetically.
        
        For now, only works correctly for odd nvot"""
        scores = sorted(scores)
        nvot = len(scores)
        lo = hi = mid = nvot // 2
        base = scores[mid]
        while (hi < nvot and scores[hi] == base):
            hi += 1
        while (lo > 0 and scores[lo] == base):
            lo -= 1
            
        if (hi-mid) == (mid-lo):
            return base
        elif (hi-mid) < (mid-lo):
            return base + (hi-mid) / nvot
        else:
            return base - (mid-lo) / nvot
        
class Bucklin(Method):
    def candScore(self, scores):
        """For now, only works correctly for odd nvot"""
        scores = sorted(scores)
        nvot = len(scores)
        i = mid = nvot // 2
        base = scores[i]
        while (i > nvot and scores[-i] == base):
            i += 1
        mod = mid * (base + 0.5) / (i - 0.5)
        if mod > base:
            return mod
        return base - ((base - mod) / (base + 0.5)) 
    
    @staticmethod #cls is provided explicitly, not through binding
    @rememberBallot
    def honBallot(cls, voter):
        """Takes utilities and returns an honest ballot (on 0..4)"""
        cutoffs = cls.baseCuts[0:3] + [max(voter)]
        return [toVote(cutoffs, util) for util in voter]
        
    
    def stratBallotFor(self, info):
        """Returns a (function which takes utilities and returns a strategic ballot)
        for the given "polling" info.""" 
        places = sorted(enumerate(info),key=lambda x:x[0]) #from high to low
        #print("places",places)
        frontrunners = (places[0][0], places[1][0], places[0][1], places[1][1])
        
        @rememberBallot
        def stratBallot(cls, voter, front=frontrunners):
            frontUtils = [voter[front[0]], voter[front[1]]] #utils of frontrunners
            if frontUtils[0] == frontUtils[1]:
                return [(4 if (util >= frontUtils[0]) else 0) for util in voter]
            else:
                if frontUtils[0] > frontUtils[1]:
                    #winner is preferred; be complacent.
                    strat = False
                else:
                    #runner-up is preferred; be strategic in iss run
                    strat = True
                    #sort cuts high to low
                    frontUtils = (frontUtils[1], frontUtils[0])
                setattr(voter, cls.__name__ + "_isStrat", strat)
                top = max(voter)
                cutoffs = [(  (min(frontUtils[0], self.baseCuts[i])) 
                                 if (i < floor(front[3]) - 1) else 
                            ( (frontUtils[1]) 
                                 if (i < floor(front[2]) + 1) else
                              min(top, self.baseCuts[i])
                              ))
                           for i in range(4)]
                return [toVote(cutoffs, util) for util in voter]
        return stratBallot
    
        
def doVse(model, methods, nvot, ncand, niter):
    """A harness function which creates niter elections from model and finds three kinds
    of VSE for all methods given.
    
    for instance:
    vses = br.doVse(br.PolyaModel(), [br.Score(), br.Mav()], 100, 4, 100)
    """
    vses = []
    for i in range(niter):
        electorate = model(nvot, ncand)
        vse = []
        for method in methods:
            vse.append(method.vseOn(electorate))
        vses.append(vse)
        print(i,vse)
    return vses
            
def printVse(results):
    """print the result of doVse in an accessible format.
    for instance:
    br.printVse(vses)
    """
    for i in range(len(results[0])):
        print(results[0][i][3], 
              [mean([result[i][j] for result in results]) 
                  for j in range(len(results[0][0]) - 1)],
              mean(
                   [(0 if result[i][0]==result[i][2] else 1)
                        for result in results]
                   )
              )
        
def saveResults(results, fn):
    out = open(fn, )
    

if __name__ == "__main__":
    import doctest
    doctest.testmod()